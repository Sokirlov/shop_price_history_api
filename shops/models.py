from datetime import datetime
from sqlalchemy import String, ForeignKey, select, cast, Date, and_, desc, func
from sqlalchemy.orm import relationship, Mapped, mapped_column, selectinload
from settings.database import Base, AsyncSessionLocal


class Shop(Base):
    """ Модель Магазину """
    __tablename__ = "shops"

    name: Mapped[str] = mapped_column(nullable=False, unique=True)
    url: Mapped[str | None]

    # Зв'язок з категоріями
    categories: Mapped[list["Category"]] = relationship("Category", back_populates="shop", cascade="all, delete-orphan")

    def __str__(self):
        return self.name


class Category(Base):
    """ Модель Категорії """
    __tablename__ = "categories"

    name: Mapped[str]
    url: Mapped[str]

    shop_id: Mapped[int] = mapped_column(ForeignKey("shops.id"))

    # Зв'язок з
    shop: Mapped["Shop"] = relationship("Shop", back_populates="categories")
    products = relationship("Product", back_populates="category", cascade="all, delete")

    #
    def __str__(self):
        return self.name


class Product(Base):
    """ Модель Товару """
    __tablename__ = "products"

    name: Mapped[str]
    url: Mapped[str | None]
    img_src: Mapped[str | None]
    packaging: Mapped[str | None] = mapped_column(String(50))
    in_stock: Mapped[bool] = mapped_column(default=False)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="CASCADE"))
    price_change: Mapped[float | None] = mapped_column(default=0.0, nullable=True)

    # Зв'язок з категорією
    category = relationship("Category", back_populates="products")
    prices = relationship("Price", back_populates="product", cascade="all, delete",
                          # primaryjoin="and_(Product.category_id==Category.id, limit 2)",
                          order_by=lambda: desc(Price.updated_at))

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
                # instance = instance
                instance.in_stock = in_stock if price > 0.0 else True
                instance.img_src = img_src
                instance.packaging = packaging
                # instance.price_change = await cls.validate_change_price(session, instance.id, price)
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

            prc, price_cange = await Price.get_or_create(price=price, product_id=instance.id)
            if isinstance(price_cange, float):
                instance.price_change = price_cange
            session.add(instance)
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
            print(f'kwargs -> {base_query.compile(compile_kwargs={"literal_binds": True})}')

        elif not kwargs.get("related"):
            kwargs.update(related='prices')

        results = await super().filter_by_(**kwargs)
        return results

    def __str__(self):
        return f"{self.name}"


class Price(Base):
    __tablename__ = "price"

    price: Mapped[float]
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))

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
