from elasticsearch import AsyncElasticsearch
from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse

from settings.config import settings
from shops.models import Shop, Category, Product

router = APIRouter()
templates = settings.templates


@router.get("/", response_class=HTMLResponse)
async def read_item(request: Request):
    objects = await Shop.get_all_async()
    return templates.TemplateResponse(request=request,
                                      name="category.html",
                                      context={"title": "Shops", "items": objects})


@router.get("/s")
async def search(q: str):
    es = AsyncElasticsearch("http://elastic_search:9200")
    res = await es.search(
        index="products",
        size=500,
        sort=['last_price:desc',],
        query={
            "match": {
                "name": {
                    "query": q,
                    "operator": "and"
                }
            }
            # "fuzzy": {
            #     "name": {
            #         "value": q,
            #         "fuzziness": "AUTO"
            #     }
            # },
            # "wildcard": {
            #     "name": {
            #         "value": f"*{q}*",
            #         "case_insensitive": True
            #     }
            # }
            # "prefix": {
            #     "name": q.lower()
            # }
        }
    )
    return [hit["_source"] for hit in res["hits"]["hits"]]

@router.get("/search", response_class=HTMLResponse)
async def get_search_page(request: Request):
    return templates.TemplateResponse("search.html", {"request": request})


@router.get("/{item_id}", response_class=HTMLResponse)
async def read_item(request: Request,
                    item_id: int,
                    page: int = Query(1, ge=1),
                    page_size: int = Query(20, ge=1)):
    offset = (page - 1) * page_size
    objects = await Category.filter_by_(shop_id=item_id,
                                        related='shop',
                                        limit=page_size,
                                        offset=offset)
    objects["page"] = page
    return templates.TemplateResponse(request=request,
                                      name="category.html",
                                      context={"title": "Category", **objects})


@router.get("/{shop_id}/{item_id}", response_class=HTMLResponse)
async def read_item(
        request: Request, item_id: int|str,
        page: int = Query(1, ge=1),
        page_size: int = Query(30, ge=1),
        only_changed: str = Query(None, description="cheaper, expensive, no_change"),
        ordered: str = Query(None),
        direction: str = Query(None),
):
    offset = (page - 1) * page_size
    try:
        item_id = int(item_id)
        query = dict(
            category_id=int(item_id),
            ordered=[ordered, ] if ordered else ['in_stock', 'name', ],
            related=['category', 'prices', 'category.shop'],
            only_changed=only_changed,
            limit=page_size,
            offset=offset,
            direction=direction
        )
    except ValueError:
        query = dict(
            ordered=[ordered, ] if ordered else ['in_stock', 'name', ],
            related=['category', 'prices', 'category.shop'],
            only_changed=only_changed if only_changed else "expensive",
            limit=page_size,
            offset=offset,
            direction=direction
        )
    objects = await Product.filter_by_(**query)
    objects["page"] = page
    return templates.TemplateResponse(request=request, name="goods.html", context={"title": "Goods", **objects})

@router.get("/{shop_id}/{category_id}/{good_id}", response_class=HTMLResponse)
async def read_item(request: Request, good_id: int):
    objects = await Product.filter_by_(id=good_id, related=['category', 'prices', 'category.shop'])
    if objects:
        objects = objects
    objects["page"] = 0
    return templates.TemplateResponse(request=request, name="goods.html", context={"title": 'God', **objects})


