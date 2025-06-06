from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import String, ForeignKey, select, cast, Date, and_, desc, asc, tuple_, update, case, func, Numeric
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
    categories: Mapped[list["Category"]] = relationship(
        "Category", back_populates="shop", cascade="all, delete-orphan")

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
    last_price: Mapped[float | None] = mapped_column(default=0.0, nullable=True)
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
        if not self.price_change or self.price_change is None or self.price_change == 0.0:
            self.price_change = price
            print(f"[price.setter] PRICE = {self.price_change}")
        else:
            self.price_change = price - self.last_price

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

        change = {
            "no_change": [cls.price_change == 0.0, cls.last_price > 0.0],
            "expensive": [cls.price_change > 0.0, cls.last_price > 0.0],
            "cheaper": [cls.price_change < 0.0, cls.last_price > 0.0],
        }

        if kwargs.get("only_changed"):
            filter_params = cls._filter_kwargs_by_atribute_(**kwargs)
            base_query = select(cls).filter_by(**filter_params).filter(*change.get(kwargs["only_changed"]))
            kwargs.update(base_query=base_query)
            print("kwargs", kwargs)
        elif not kwargs.get("related"):
            kwargs.update(related='prices')

        if kwargs.get("direction") == "desc" and kwargs.get("ordered"):
            kwargs.update(ordered=[desc(i) for i in kwargs.get("ordered")])

        elif kwargs.get("ordered"):
            kwargs.update(ordered=kwargs.get("ordered"))

        # kwargs = {k:v for k,v in kwargs.items() if v is not None}
        print("kwargs", kwargs)

        results = await super().filter_by_(**kwargs)

        return results

    @classmethod
    async def update_or_create_bulb(cls, products: list[dict[str, str | int]]):
        results_product = await cls.get_or_create_bulb(products)  # returned get and create objects togather
        print('products', products)

        prices_ = [
            dict(price=product['price'], product_id=product_.id)
            for product in products
            for product_ in results_product
            if product_.url == product['url']
        ]
        only_created = await Price.create_bulb(prices_)

        if only_created:
            product_ids = [i.product_id for i in only_created]
            price_map = {i.product_id: i.price for i in only_created}
            in_stock_map = {i.product_id: True if i.price == 0.0 else False for i in only_created}

            stmt = (
                update(Product)
                .filter(Product.id.in_(product_ids))
                .values(
                    # Оновлюємо last_price на нову ціну
                    last_price=case(price_map, value=Product.id),
                    # Обчислюємо зміну ціни: нова ціна - поточна ціна в базі
                    price_change=func.round(
                        (case(price_map, value=Product.id) - func.coalesce(Product.last_price, 0)).cast(Numeric),
                        2
                    ),
                    # оновлюємо статус товару
                    in_stock=case(in_stock_map, value=Product.id),
                    updated_at=datetime.now(timezone.utc),
                )
                .returning(Product.id)
            )
            print('[update_or_create_bulb] stmt:', stmt.compile(compile_kwargs={'literal_binds': True}))
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
        stmt = (
            select(price_alias.product_id, price_alias.price)
            .order_by(price_alias.product_id, desc(price_alias.updated_at))
        )
        print(f"stmt:{stmt.compile(compile_kwargs={'literal_binds': True})}")

        # Основний запит
        result = await session.execute(stmt)
        return result

    @classmethod
    async def create_bulb(cls, prices: list) -> list["Price"]:
        """ Return  only created objects """

        today = datetime.today().date()
        product_list = [i['product_id'] for i in prices]

        async with AsyncSessionLocal() as session:
            # збираємо по списку додані сьогодні
            result = await session.execute(
                select(Price.product_id)
                .filter(cast(Price.created_at, Date) == today, )
                .where(Price.product_id.in_(product_list))
            )
            existing_prices = result.scalars().all()

            # обʼєкти які треба створити
            to_create = [
                Price(product_id=price_['product_id'], price=price_['price'])
                for price_ in prices
                if price_['product_id'] not in existing_prices
            ]
            session.add_all(to_create)
            await session.commit()
        print(f'PRICE+> {to_create}')
        return to_create
