from pydantic import BaseModel, computed_field, field_serializer, Field
from typing import Optional, List
from datetime import datetime
from settings.config import settings


class CreateCategorySchema(BaseModel):
    name: str
    url: str
    shop_id: int

class ShopCategorySchema(BaseModel):
    id: int
    name: str
    url: str
    shop_id: int

    class Config:
        from_attributes = True

    @computed_field
    def link(self) -> str:
        return f"{settings.BASE_URL}/api/{self.shop_id}/{self.id}"

    @property
    def id(self) -> int:
        return self.__dict__.get('id')


class ShopSchema(BaseModel):
    id: int
    name: str
    url: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True

    @computed_field
    def link(self) -> str:
        return f"{settings.BASE_URL}/api/{self.id}"


class PriceSchema(BaseModel):
    id: int
    price: float | None = None
    product_id: int
    created_at: str | datetime = None
    updated_at: str | datetime = None

    @field_serializer('updated_at')
    def serialize_updated_at(self, updated_at: datetime, _info) -> str | None:
        return updated_at.strftime('%Y-%m-%d')

    # class Config:
    #     from_attributes = True




class ProductCreateSchema(BaseModel):
    name: str = Field(..., max_length=255)
    url: Optional[str] = None
    img_src: Optional[str] = None
    packaging: Optional[str] = Field(None, max_length=50)
    in_stock: bool = False
    category_id: int
    price: Optional[float] = 0.0



class ProductResponseSchema(BaseModel):
    name: str = Field(..., max_length=255)
    url: Optional[str] = None
    img_src: Optional[str] = None
    packaging: Optional[str] = Field(None, max_length=50)
    in_stock: bool = False
    category_id: int
    price_change: Optional[float] = 0.0


class ProductSchema(BaseModel):
    id: int
    name: str
    url: str
    img_src: Optional[str] = None
    packaging: str
    in_stock: bool
    prices: List[PriceSchema]
    category_id: int
    # category: ShopCategorySchema
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CategorySchema(BaseModel):
    id: int
    name: str
    url: str
    shop_id: int
    products: List[ProductSchema]

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
