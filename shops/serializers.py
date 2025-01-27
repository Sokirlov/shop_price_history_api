from pydantic import BaseModel, computed_field, field_serializer, Field
from typing import Optional, List
from datetime import datetime
from settings.config import settings


class ShopSchemaPOST(BaseModel):
    name: str
    url: str


class ShopSchemaGET(ShopSchemaPOST):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True

    @computed_field
    def link(self) -> str:
        return f"{settings.BASE_URL}/api/{self.id}"


class CategorySchemaPOST(BaseModel):
    name: str
    url: str
    shop_id: int


class CategorySchemaGET(CategorySchemaPOST):
    id: int

    class Config:
        from_attributes = True

    @computed_field
    def link(self) -> str:
        return f"{settings.BASE_URL}/api/{self.shop_id}/{self.id}"

    @property
    def id(self) -> int:
        return self.__dict__.get('id')


class ProductSchemaPOST(BaseModel):
    name: str = Field(..., max_length=255)
    url: Optional[str] = None
    img_src: Optional[str] = None
    packaging: Optional[str] = Field(None, max_length=50)
    in_stock: bool = False
    category_id: int
    price: Optional[float] = 0.0


class ProductSchemaGET(ProductSchemaPOST):
    id: int
    price_change: Optional[float] = 0.0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PriceSchemaGET(BaseModel):
    id: int
    price: float | None = None
    product_id: int
    created_at: str | datetime = None
    updated_at: str | datetime = None

    @field_serializer('updated_at')
    def serialize_updated_at(self, updated_at: datetime, _info) -> str | None:
        return updated_at.strftime('%Y-%m-%d')


class ProductPricesSchemaGET(BaseModel):
    id: int
    name: str
    url: str
    img_src: Optional[str] = None
    packaging: str
    in_stock: bool
    prices: List[PriceSchemaGET]
    category_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
