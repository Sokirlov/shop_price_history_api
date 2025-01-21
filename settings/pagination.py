from typing import List, Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    title: str | None = None
    page: int
    page_size: int
    total_items: int
    total_pages: int
    items: List[T]
