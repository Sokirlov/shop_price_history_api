import asyncio
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import MetaData, func, create_engine, inspect
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker, selectinload, DeclarativeBase, Mapped, mapped_column, InstrumentedAttribute
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from .config import settings

logging.basicConfig(
    # filename=logfile,
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

# Створення двигуна
engine = create_engine(
    settings.database_url_sync,
    echo=False,
    pool_size=5,  # основних підключень
    max_overflow=10,  # додаткові навантаження
)
sessions_sync = sessionmaker(bind=engine)

# Створення асинхронного двигуна
async_engine = create_async_engine(settings.database_url_async, echo=False, future=True)
AsyncSessionLocal = sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


class Base(DeclarativeBase):
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now())
    updated_at: Mapped[datetime] = mapped_column(default=datetime.now(), onupdate=func.now())

    __abstract__ = True
    metadata = MetaData()

    repr_cols_num = 4
    repr_cols = tuple()

    def __repr__(self) -> str:
        if settings.DEBUG:
            col = []
            for idx, c_name in enumerate(self.__table__.columns.keys()):
                if idx < self.repr_cols_num or c_name in self.repr_cols:
                    col.append(f"{c_name}={getattr(self, c_name)!r}")
            return f"\n<class:{self.__class__.__name__}\t|\t({',\t'.join(col)})>"
        return f'<class:{self.__class__.__name__}>'

    @classmethod
    def get_relationships(cls):
        return [(rel.key, rel.mapper.class_) for rel in inspect(cls).relationships]

    @classmethod
    def _filter_kwargs_by_atribute_(cls, **kwargs) -> dict:
        """
        Фільтрує kwargs і залишає тільки ті ключі, які відповідають полям таблиці SQLAlchemy моделі.

        :param model: SQLAlchemy модель, яка наслідує Base
        :param kwargs: словник значень
        :return: відфільтрований словник
        """
        # Отримуємо набір імен усіх атрибутів моделі, які є колонками або relationship
        model_fields = {attr for attr, value in vars(cls).items() if isinstance(value, InstrumentedAttribute)}
        # Повертаємо тільки ті пари ключ-значення, які є в полях моделі
        return {key: value for key, value in kwargs.items() if key in model_fields}

    @classmethod
    def validate_relationships(cls, relateds: list[str]) -> list:
        relations = []
        for related in relateds:
            relation_ = getattr(cls, related, None)
            if relation_ is None:
                raise ValueError(f"Relationship '{related}' not found on model '{cls.__name__}'")
            relations.append(selectinload(relation_))
        return relations

    @classmethod
    async def create(cls, **kwargs):
        request = cls._filter_kwargs_by_atribute_(**kwargs)
        async with AsyncSessionLocal() as session:
            instance = cls(**request)
            session.add(instance)
            await session.commit()
            await session.refresh(instance)
        logger.debug(f'class {cls.__name__} created: {instance}')
        return instance

    @classmethod
    async def get_or_create(cls, **kwargs):
        """
        Повертає існуючий об'єкт або створює новий.
        :param kwargs: Поля для пошуку об'єкта.
        :return: Tuple (об'єкт, створено чи ні).
        """
        request = cls._filter_kwargs_by_atribute_(**kwargs)
        async with AsyncSessionLocal() as session:
            instance = await session.execute(select(cls).filter_by(**request))
            instance = instance.scalar()

        if instance:
            return instance, False

        instance = await cls.create(**request)
        return instance, True

    @classmethod
    async def create_bulk(cls, objects: list[dict]):
        """
        Створює кілька об'єктів у базі даних асинхронно.

        :param session: AsyncSession
        :param objects: Список словників з параметрами для створення об'єктів
        :return: Список створених об'єктів
        """

        instances = []  # Створюємо об'єкти
        for obj in objects:
            data = cls._filter_kwargs_by_atribute_(**obj)
            instances.append(cls(**data))

        async with AsyncSessionLocal() as session:
            session.add_all(instances)  # Додаємо їх у сесію

            await session.commit()  # Коммітимо зміни
            for instance in instances:
                await session.refresh(instance)
            return instances

    @classmethod
    async def get_all_async(cls, related: Optional[str] = None) -> list:

        stmt = select(cls)
        if related:
            relation = getattr(cls, related, None)
            if relation is None:
                raise ValueError(f"Relationship '{related}' not found on model '{cls.__name__}'")
            stmt = stmt.options(selectinload(relation))

        async with AsyncSessionLocal() as session:
            result = await session.execute(stmt)

            try:
                shops = result.scalars().all()
            except Exception as e:
                print('Exception', e)
                shops = result.all()
            print('get all shops', shops)
            return shops

    @classmethod
    async def filter_by_(cls, **kwargs) -> dict:
        """
        ordered: Optional[list] = None,
        related: Optional[str] = None,
        limit: Optional[int] = 10,
        offset: Optional[int] = 0,
        :param kwargs:
        :return:
        """
        limit = kwargs.get('limit', 10)
        offset = kwargs.get('offset', 0)
        ordered = kwargs.get('ordered')
        related = kwargs.get('related')

        filter_params = cls._filter_kwargs_by_atribute_(**kwargs)
        stmt = kwargs.get('base_query', select(cls).filter_by(**filter_params))

        if ordered:
            stmt = stmt.order_by(*ordered)

        if related:
            if isinstance(related, str):
                relations = cls.validate_relationships([related, ])
            elif isinstance(related, list):
                relations = cls.validate_relationships(related)
            else:
                raise Exception(f"Unsupported type of related: {type(related)}")
            stmt = stmt.options(*relations)

        result = await cls._paginate_objects_(stmt, offset, limit)
        return result

    @classmethod
    async def _paginate_objects_(cls, base_query, offset: int, limit: int) -> dict:
        count_query = select(func.count()).select_from(base_query.subquery())
        limited_query = base_query.limit(limit).offset(offset)

        print(f'\ncount_query: {count_query.compile(compile_kwargs={'literal_binds': True})}\n\n'
              f'limited_query: {limited_query.compile(compile_kwargs={'literal_binds': True})}\n\n')

        async with AsyncSessionLocal() as session:
            # Виконання запитів
            total_items = await session.execute(count_query)
            limited_objects = await session.execute(limited_query)

        total_items = total_items.scalar()
        limited_objects = limited_objects.unique()
        items = limited_objects.scalars().all()
        total_pages = total_items // limit
        page_ = offset // limit

        return dict(page=page_, page_size=limit, total_items=total_items, total_pages=total_pages, items=items)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# pip install alembic
# alembic init alembic


# Створення міграцій
# alembic revision --autogenerate -m "Опис змін"

# Застосування міграцій
# alembic upgrade head

# Оновлення міграцій (якщо є зміни)
# alembic revision --autogenerate -m "Опис нових змін"
# alembic upgrade head
