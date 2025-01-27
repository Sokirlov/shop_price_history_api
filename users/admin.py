

import bcrypt
import datetime


from pydantic import ValidationError
from sqlalchemy import select, func
from fastadmin import (SqlAlchemyModelAdmin, register, action, DashboardWidgetAdmin, DashboardWidgetType,
                       register_widget, WidgetType)

from settings.database import AsyncSessionLocal
from users.models import User

import os
from dotenv import load_dotenv
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)


@register(User, sqlalchemy_sessionmaker=AsyncSessionLocal)
class UserAdmin(SqlAlchemyModelAdmin):
    list_display = ("id", "username", "is_superuser", "is_active")
    list_editable = ("is_superuser", "is_active")
    list_display_links = ("id", "username")
    list_filter = ("username", "is_superuser", "is_active")
    search_fields = ("id", "username",)
    actions = (*SqlAlchemyModelAdmin.actions, "activate", "deactivate",)

    fieldsets = (
        (None, {"fields": ("username", "hash_password")}),
        ("Permissions", {"fields": ("is_active", "is_superuser")}),
    )
    formfield_overrides = {
        "username": (WidgetType.SlugInput, {"required": True}),
        "hash_password": (WidgetType.PasswordInput, {"passwordModalForm": True}),
    }

    async def authenticate(self, username, password):
        print('authenticate', username, password)
        sessionmaker = self.get_sessionmaker()
        async with sessionmaker() as session:
            query = select(User).filter_by(username=username,
                                           # hash_password=password,
                                           is_superuser=True)
            result = await session.scalars(query)
            user = result.first()
            print(f'USER: {username} => {user}')

            if not user:
                print("\nIS ONLY CHANGED USER .. {}\n\n".format(username))
                return None
            print("Try validate user:{username}".format(username=username))
            if not bcrypt.checkpw(password.encode(), user.hash_password.encode()):
                return None

            return user.id

    async def change_password(self, user_id: int, password: str):
        """
        Зміна пароля користувача.
        """
        sessionmaker = self.get_sessionmaker()
        async with sessionmaker() as session:
            user = await session.get(User, user_id)
            if not user:
                raise ValidationError("User not found.")
            # Хешуємо новий пароль і зберігаємо його в БД
            user.hash_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            session.add(user)
            await session.commit()
        return {"message": "Password successfully changed!"}

    @action(description="Set as active")
    async def activate(self, ids: list[int]) -> None:
        await self.model_cls.filter(id__in=ids).update(is_active=True)

    @action(description="Deactivate")
    async def deactivate(self, ids: list[int]) -> None:
        await self.model_cls.filter(id__in=ids).update(is_active=False)


@register_widget
class UsersDashboardWidgetAdmin(DashboardWidgetAdmin):
    title = "Users"
    dashboard_widget_type = DashboardWidgetType.ChartLine

    x_field = "date"
    x_field_filter_widget_type = WidgetType.DatePicker
    x_field_filter_widget_props: dict[str, str] = {"picker": "month"}  # noqa: RUF012
    x_field_periods = ["day", "week", "month", "year"]  # noqa: RUF012

    y_field = "count"

    async def get_data(self,
                       min_x_field: str | None = None,
                       max_x_field: str | None = None,
                       period_x_field: str | None = None) -> dict:

        if not min_x_field:
            min_x_field_date = datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(days=360)
        else:
            min_x_field_date = datetime.datetime.fromisoformat(min_x_field)

        if not max_x_field:
            max_x_field_date = datetime.datetime.now(tz=datetime.UTC) + datetime.timedelta(days=1)
        else:
            max_x_field_date = datetime.datetime.fromisoformat(max_x_field)

        if not period_x_field or period_x_field not in (self.x_field_periods or []):
            period_x_field = "month"

        query = select(
            func.to_char(func.date_trunc(period_x_field, func.timezone("UTC", User.created_at)), "dd/mm/yyyy").label(
                "date"),
            func.count(User.id).label("count"),
        ).where(
            func.timezone("UTC", User.created_at) >= min_x_field_date,
            func.timezone("UTC", User.created_at) <= max_x_field_date,
        ).group_by(
            "date"
        ).order_by(
            "date"
        )

        async with AsyncSessionLocal() as session:
            result = await session.execute(query)

        return {
            "results": result.scalars().all(),
            "min_x_field": min_x_field_date.isoformat(),
            "max_x_field": max_x_field_date.isoformat(),
            "period_x_field": period_x_field,
        }
