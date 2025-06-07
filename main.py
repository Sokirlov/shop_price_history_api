from elasticsearch import AsyncElasticsearch
from fastapi import FastAPI
from fastadmin import fastapi_app as admin_app

# from starlette.middleware.cors import CORSMiddleware

from shops.urls import router as shop_router
from settings.config import settings
from settings.service import import_admin_modules
from settings.elastic import create_index, index_products_from_db
from settings.database import async_engine, Base

import_admin_modules()


app = FastAPI()

@app.on_event("startup")
async def startup():
    from users.models import User
    # Ініціалізація таблиць у базі даних
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await create_index()
    # await index_products_from_db()


app.mount("/admin", admin_app)
app.mount("/static", settings.static, name="static")

@app.post("/reindex")
async def reindex_products():
    await index_products_from_db()
    return {"status": "done"}

app.include_router(shop_router)
#
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["http://localhost:5173"],  # Дозволені джерела (наприклад, ваш фронтенд)
#     allow_credentials=True,
#     allow_methods=["GET", "POST", "PUT", "DELETE"],  # Які методи дозволено
#     allow_headers=["*"],  # Які заголовки дозволено
# )
