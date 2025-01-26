from typing import Union, List
from fastapi import Query, APIRouter, HTTPException, Form

from settings.pagination import PaginatedResponse
from .models import Shop, Product, Category
from .serializers import ShopSchema, ProductSchema, ShopCategorySchema, ProductResponseSchema, CreateCategorySchema, \
    ProductCreateSchema

router = APIRouter()


@router.get("/", response_model=List[ShopSchema])
async def get_prices():
    prices = await Shop.get_all_async()
    return prices


@router.post("/", response_model=ShopSchema)
async def create_shop(name: str = Form(),
                      url: str = Form()):
    item, _ = await Shop.get_or_create(name=name, url=url)

    if not item:
        raise HTTPException(status_code=400, detail="Failed to create category")

    return item




@router.get("/{item_id}", response_model=PaginatedResponse[ShopCategorySchema], description="Get shop category by id")
async def get_prices(item_id: int,
                     page: int = Query(1, ge=1),
                     page_size: int = Query(10, ge=1)):
    offset = page * page_size if page > 1 else 0

    results: dict = await Category.filter_by_(shop_id=item_id, limit=page_size, offset=offset)
    results['page'] = page
    return PaginatedResponse(**results)



@router.post("/categories", response_model=list[ShopCategorySchema])
async def create_categories(categories: list[CreateCategorySchema]):
    print(f"categories={categories}")
    data = [i.__dict__ for i in categories]
    items = await Category.get_or_create_bulb(data)
    return items



@router.post("/products", response_model=list[ProductResponseSchema])
async def create_products(products: list[ProductCreateSchema]):
    print(f"create_products={type(products)}")
    data = [i.__dict__ for i in products]
    items = await Product.update_or_create_bulb(data)

    return items




@router.post("/{shop_id}", response_model=ShopCategorySchema)
async def create_category(shop_id: int,
                          name: str = Form(),
                          url: str = Form()):
    item, _ = await Category.get_or_create(shop_id=shop_id, name=name, url=url)

    if not item:
        raise HTTPException(status_code=400, detail="Failed to create category")

    return item


@router.get("/{shop_id}/{category_id}", response_model=PaginatedResponse[ProductSchema])
async def read_item(category_id: int,
                    only_changed: Union[int, None] = None,
                    page: int = Query(1, ge=1),
                    page_size: int = Query(10, ge=1)):
    offset = page * page_size if page > 1 else 0

    results = await Product.filter_by_(category_id=category_id,
                                       ordered=['in_stock', ],
                                       related='prices',
                                       limit=page_size,
                                       offset=offset,
                                       only_changed=bool(only_changed)
                                       )
    results['page'] = page
    return PaginatedResponse(**results)


@router.post("/{shop_id}/{category_id}", response_model=ProductResponseSchema)
async def read_item(category_id: int,
                    name: str = Form(),
                    url: str = Form(),
                    img_src: str = Form(None),
                    packaging: str = Form(None),
                    in_stock: bool = Form(False),
                    price: float = Form(0.0)):
    item, _ = await Product.update_or_create(category_id=category_id,
                                             name=name,
                                             url=url,
                                             img_src=img_src,
                                             packaging=packaging,
                                             in_stock=in_stock,
                                             price=price
                                             )

    return item
