from fastadmin import SqlAlchemyModelAdmin, register, SqlAlchemyInlineModelAdmin

from settings.database import AsyncSessionLocal
from shops.models import Shop, Category, Product, Price

@register(Shop, sqlalchemy_sessionmaker=AsyncSessionLocal)
class ShopAdmin(SqlAlchemyModelAdmin):
    list_display = ("id", "name", "url", "created_at", "updated_at")
    list_display_links = ("id", "name")
    list_filter = ("created_at", "updated_at")
    search_fields = ("name",)
    readonly_fields = ("id", "created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("name", "url")}),
    )


@register(Category, sqlalchemy_sessionmaker=AsyncSessionLocal)
class CategoryAdmin(SqlAlchemyModelAdmin):
    list_display = ("id", "name", "url", "created_at", "updated_at", "shop")
    list_display_links = ("id", "name")
    list_filter = ("shop",)
    ordering = ("-created_at",)
    search_fields = ("name",)
    readonly_fields = ("id", "created_at", "updated_at",)
    fieldsets = (
        (None, {"fields": ("name", "url")}),
        ('Shop', {"fields": ("shop",)}),
    )

class PriceAdmin(SqlAlchemyInlineModelAdmin):
    model = Price
    db_session_maker = AsyncSessionLocal
    list_display = ("id", "price", "product")
    readonly_fields = ("id", "created_at", "updated_at",)

@register(Product, sqlalchemy_sessionmaker=AsyncSessionLocal)
class ProductAdmin(SqlAlchemyModelAdmin):
    exclude = ("created_at", "updated_at")
    list_display = ("id", "name", "url", "price_change", "created_at", "updated_at", "category",)
    list_display_links = ("id", "name")
    list_filter = ("category",)
    search_fields = ("name",)
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")
    inlines = (PriceAdmin,)
    fieldsets = (
        (None, {"fields": ("name", "url", "category", "prices")}),
        # ('Price', {"fields": ("prices",)}),
    )



@register(Price, sqlalchemy_sessionmaker=AsyncSessionLocal)
class PriceAdmin(SqlAlchemyModelAdmin):
    list_display = ("id", "price", "product", "created_at", "updated_at")
    list_display_links = ("id", "price")
    list_filter = ("created_at", "updated_at")
    readonly_fields = ("id", "created_at", "updated_at",)
    fieldsets = (
        (None, {"fields": ("price", "product")}),
    )