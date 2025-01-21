from fastapi import APIRouter
from .apis import router as products_router
from .views import router as categories_router

router = APIRouter()
router.include_router(products_router, prefix="/api", tags=["apis"])
router.include_router(categories_router, prefix="", tags=["Views"])
