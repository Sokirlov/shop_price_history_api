from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import String, ForeignKey, select, cast, Date, and_, desc, tuple_, update, case, func
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, Mapped, mapped_column, aliased
from settings.database import Base, AsyncSessionLocal, get_session


# TODO рефакторити код, винести в методах "..._bulb" спільний функціонал
#  по розділеню на існуючі та нові обʼєкти. Виправити оновлення price_change,
#  спростити та зменшити кількість запитів до БД



class Shop(Base):
    """ Модель Магазину """
    __tablename__ = "shops"

    name: Mapped[str] = mapped_column(nullable=False, unique=True)
    url: Mapped[str | None]

    # Зв'язок з категоріями
    categories: Mapped[list["Category"]] = relationship("Category", back_populates="shop", cascade="all, delete-orphan")

    @hybrid_property
    def lower_name(self):
        return func.lower(self.name)

    @property
    async def _filter_kwargs_by_atribute_(cls, **kwargs) -> dict:
        fields_from_kwargs = super()._filter_kwargs_by_atribute_(**kwargs)
        fields_from_kwargs['lower_name'] = fields_from_kwargs.pop('name')
        return fields_from_kwargs

    def __str__(self):
        return self.name


class Category(Base):
    """ Модель Категорії """
    __tablename__ = "category"

    name: Mapped[str]
    url: Mapped[str]

    shop_id: Mapped[int] = mapped_column(ForeignKey("shops.id"))

    # Зв'язок з
    shop: Mapped["Shop"] = relationship("Shop", back_populates="categories")
    products = relationship("Product", back_populates="category", cascade="all, delete")

    @hybrid_property
    def lower_name(self):
        return func.lower(self.name)

    def __str__(self):
        return self.name


class Product(Base):
    """ Модель Товару """
    __tablename__ = "product"

    name: Mapped[str]
    url: Mapped[str | None]
    img_src: Mapped[str | None]
    packaging: Mapped[str | None] = mapped_column(String(50))
    in_stock: Mapped[bool] = mapped_column(default=False)
    category_id: Mapped[int] = mapped_column(ForeignKey("category.id", ondelete="CASCADE"))
    price_change: Mapped[float | None] = mapped_column(default=0.0, nullable=True)

    # Зв'язок з категорією
    category = relationship("Category", back_populates="products")
    prices = relationship("Price", back_populates="product", cascade="all, delete",
                          order_by=lambda: desc(Price.updated_at))

    @hybrid_property
    def price(self):
        return self.price_change

    @price.setter
    def price(self, price):
        if self.price_change is None or self.price_change == 0.0:
            self.price_change = price
        else:
            self.price_change = price - self.price_change
        # print(f"[price.setter] PRICE = {self.price_change}")

    @staticmethod
    async def validate_change_price(session: AsyncSessionLocal, product_id: int, new_price: float) -> float:
        result = await session.execute(
            select(Price)
            .where(Price.product_id == product_id)
            .order_by(desc(Price.updated_at))
        )
        if result:
            price_ = result.scalars().first()
            change = round(new_price - price_.price, 2)
        else:
            change = new_price
        return change

    @classmethod
    async def update_or_create(cls, category_id: int, name: str, price: float, **kwargs):
        #        url: str, price: float, in_stock: bool,
        # packaging: str, img_src: Optional[str] = None):
        props_ = cls._filter_kwargs_by_atribute_(**kwargs)

        packaging = props_.pop('packaging', None)
        in_stock = props_.pop('in_stock', False)
        img_src = props_.pop('img_src', None)
        if price == 0.0:
            in_stock = True

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(cls)
                .filter_by(category_id=category_id, name=name, packaging=packaging)
            )

            instance = result.scalars().first()
            if instance:
                instance.in_stock = in_stock if price > 0.0 else True
                instance.img_src = img_src
                instance.packaging = packaging
                session.add(instance)
                await session.flush()
            else:
                # Якщо не знайдено, створити новий об'єкт
                instance = Product(name=name,
                                   category_id=category_id,
                                   in_stock=in_stock,
                                   packaging=packaging,
                                   img_src=img_src,
                                   price_change=price,
                                   **props_
                                   )
                session.add(instance)
                await session.commit()
            print('add price', price)
            prc, price_change = await Price.get_or_create(price=price, product_id=instance.id)
            print(f'price change: {price_change}')
            if isinstance(price_change, float):
                instance.price_change = price_change

            # session.add(instance)
            await session.commit()
            await session.refresh(instance)

        return instance, True

    @classmethod
    async def filter_by_(cls, **kwargs) -> dict:

        if isinstance(kwargs.get("only_changed"), int):
            filter_params = cls._filter_kwargs_by_atribute_(**kwargs)
            base_query = select(cls).filter_by(**filter_params)

            if kwargs.get('only_changed') == 0:
                base_query = base_query.filter(cls.price_change == 0.0)
            elif kwargs.get('only_changed') > 0:
                base_query = base_query.filter(cls.price_change >= 1.0)
                kwargs.update(ordered=[desc('price_change')])

            kwargs.update(base_query=base_query)
            # print(f'kwargs -> {base_query.compile(compile_kwargs={"literal_binds": True})}')

        elif not kwargs.get("related"):
            kwargs.update(related='prices')

        results = await super().filter_by_(**kwargs)
        return results

    @classmethod
    async def objects_by_query(cls, query, **kwargs) -> Sequence:

        session  = kwargs.pop("session", get_session())
        result = await session.execute(
            select(cls).where(query)
        )
        results = result.scalars().all()
        return results

    @classmethod
    async def update_or_create_bulb(cls, products: list[dict[str, str | int]]):
        results_product = await cls.get_or_create_bulb(products)
        prices = [dict(price=product['price'], product_id=product_.id)
                  for product in products
                  for product_ in results_product
                  if product_.url == product['url']
        ]
        await Price.get_or_create_bulb(prices)

        today = datetime.today().date()
        stmt = (
            update(Product)
            .filter(cast(Product.updated_at, Date) != today,)
            .where(Product.id.in_([i['product_id'] for i in prices]))  # Вибираємо тільки потрібні продукти
            .values(
                price_change=case(
                    {i['product_id']: i['price'] for i in prices},
                    value=Product.id,
                    # else_=Product.price_change,
                ),
                updated_at=datetime.now(timezone.utc),
            )
            .returning(Product.id)
        )
        # print('stmt:', stmt.compile(compile_kwargs={'literal_binds': True}))
        async with AsyncSessionLocal() as session:
            await session.execute(stmt)
            await session.commit()

        return results_product

    @hybrid_property
    def lower_name(self):
        return func.lower(self.name)

    def __str__(self):
        return f"{self.name}"


class Price(Base):
    __tablename__ = "price"

    price: Mapped[float]
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id", ondelete="CASCADE"))

    # Зв'язок з категорією
    product = relationship("Product", back_populates="prices")

    @classmethod
    async def get_or_create(cls, price: float, product_id: int | Mapped[int]) -> tuple[Base, bool or float]:
        tody = datetime.today().date()
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Price).filter(
                and_(
                    cast(Price.created_at, Date) == tody,
                    Price.product_id == product_id
                )
            ))
            instance = result.scalars().first()
            if instance:
                change_price = False
            else:
                last_price = await session.execute(
                    select(Price).filter(Price.product_id == product_id).order_by(desc('created_at'))
                )
                last_price = last_price.scalars().first()

                if last_price:
                    change_price = abs(
                        round(price - last_price.price, 2)
                    )
                else:
                    change_price = price
                instance = cls(price=price, product_id=product_id)
                session.add(instance)
                await session.commit()
                await session.refresh(instance)

        return instance, change_price

    @staticmethod
    async def get_price_differences(session: AsyncSessionLocal, product_ids) -> dict[int, float]:
        # Підзапит для отримання останніх двох записів по кожному продукту
        subquery = (
            select(Price)
            .where(Price.product_id.in_(product_ids))
            .order_by(desc(Price.updated_at))
            .limit(2)  # Отримати лише два записи
            .subquery()
        )

        # Аліас для підзапиту
        price_alias = aliased(Price, subquery)

        stmt = select(price_alias.product_id, price_alias.price).order_by(price_alias.product_id, desc(price_alias.updated_at))
        print(f"stmt:{stmt.compile(compile_kwargs={'literal_binds': True})}")

        # Основний запит
        result = await session.execute(stmt)
        #
        # print(f'[GET Prices] {result}]')
        # # Перетворення результатів у словник {product_id: [last_price, prev_price]}
        # prices = dict().fromkeys(product_ids, [])
        # for product_id, price in result:
        #     print(f'build prices {product_id} == {price}')
        #     if product_id not in prices.keys():
        #         prices[product_id] = []
        #     prices[product_id].append(price)
        #
        # # Обчислення різниці
        # differences = {}
        # for product_id, price_list in prices.items():
        #     if len(price_list) == 2:
        #         differences[product_id] = round(price_list[0] - price_list[1], 2)
        #     else:
        #         differences[product_id] = round(price_list[0], 2)
        # print(differences)
        return result

    @classmethod
    async def get_or_create_bulb(cls, prices: list[dict[str, str | int]]) -> tuple[list[Base], dict[int, float]]:

        today = datetime.today().date()
        price_list = [i['product_id'] for i in prices]

        results_prices = []
        async with AsyncSessionLocal() as session:
            # збираємо по списку додані сьогодні
            result = await session.execute(
                select(Price).filter(
                        cast(Price.created_at, Date) == today,
                ).where(
                    Price.product_id.in_(price_list)
                )
            )
            existing_prices = result.scalars().all()

            results_prices.extend(existing_prices)
            # список існуючих обʼєктів
            existing_price_product_id = [i.product_id for i in existing_prices]

            # обʼєкти які треба створити
            to_create = [
                Price(product_id=price_['product_id'], price=price_['price'])
                for price_ in prices
                if price_['product_id'] not in existing_price_product_id
            ]
            session.add_all(to_create)
            await session.commit()
            results_prices.extend(to_create)

            differences = await cls.get_price_differences(session, price_list)
        return results_prices, differences