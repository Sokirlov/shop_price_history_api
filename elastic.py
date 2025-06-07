from elasticsearch.helpers import async_bulk
from elasticsearch import Elasticsearch, AsyncElasticsearch

from shops.models import Product

# es = Elasticsearch("http://localhost:9200")
es = AsyncElasticsearch("http://elasticsearch:9200")
if not es.ping():
    raise ValueError("Elasticsearch не відповідає")

async def create_index():
    exists = await es.indices.exists(index="products")
    if not exists:
        await es.indices.create(index="products", body={
            "settings": {
                "analysis": {
                    "filter": {
                        "autocomplete_filter": {
                            "type": "edge_ngram",
                            "min_gram": 1,
                            "max_gram": 20
                        }
                    },
                    "analyzer": {
                        "autocomplete": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": [
                                "lowercase",
                                "autocomplete_filter"
                            ]
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    "name": {
                        "type": "text",
                        "analyzer": "autocomplete",
                        "search_analyzer": "standard"
                    },
                    "last_price": {"type": "float"},
                    "price_change": {"type": "float"},
                    "category_id": {"type": "integer"},
                }
            }
        })


async def index_products_from_db():
    # result = await db.execute(select(Product))
    # async with AsyncSessionLocal() as session:

    products = await Product.get_all_async()

    print(f"I have {len(products)} products")
    actions = [
        {
            "_index": "products",
            "_id": product.id,
            "_source": {
                "id": product.id,
                "name": product.name,
                "last_price": product.last_price,
                "price_change": product.price_change,
                "category_id": product.category_id,
            },
        }
        for product in products
    ]

    await async_bulk(es, actions)


# def index_products_from_db(db: Session):
#     products = db.query(Product).all()
#     print(f"I have {len(products)} products")
#     for product in products:
#         doc = {
#             "id": product.id,
#             "name": product.name,
#             "last_price": product.last_price,
#             "price_change": product.price_change,
#         }
#         es.index(index="products", id=product.id, document=doc)
#         print(f'Updated {product.id}')