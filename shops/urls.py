from fastapi import APIRouter
from shops.apis import router as products_router
from shops.views import router as categories_router

router = APIRouter()
router.include_router(products_router, prefix="/api", tags=["apis"])
router.include_router(categories_router, prefix="", tags=["Views"])
