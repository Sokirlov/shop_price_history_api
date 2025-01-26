from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse

from settings.config import settings
from .models import Shop, Category, Product

router = APIRouter()
templates = settings.templates


@router.get("/", response_class=HTMLResponse)
async def read_item(request: Request):
    objects = await Shop.get_all_async()
    return templates.TemplateResponse(request=request,
                                      name="category.html",
                                      context={"title": "Shops", "items": objects})


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
async def read_item(request: Request,
                    item_id: int,
                    page: int = Query(1, ge=1),
                    page_size: int = Query(30, ge=1),
                    only_changed: int = Query(0, description="Value must be 0 or 1")):
    offset = (page - 1) * page_size
    query = dict(
        category_id=item_id,
        ordered=['name', 'in_stock', ],
        related=['category', 'prices'],
        limit=page_size,
        offset=offset
    )
    if only_changed:
        query["only_changed"] = only_changed

    objects = await Product.filter_by_(**query)
    print('objects', objects)
    objects["page"] = page
    for k, v in objects.items():
        print(f'{k}:{v}')
    return templates.TemplateResponse(request=request,
                                      name="goods.html",
                                      context={"title": "Goods", **objects})
