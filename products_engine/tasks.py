from decimal import Decimal

from faker import Faker

from celery_app import celery_app, get_db_session
from models import Product, ProductStatus

fake = Faker()


@celery_app.task
def generate_products(count: int, category_id: int) -> str:
    session = get_db_session()
    products = []
    for _ in range(count):
        products.append(
            Product(
                category_id=category_id,
                title=fake.catch_phrase(),
                description=fake.text(max_nb_chars=200),
                price=Decimal(
                    str(round(fake.pyfloat(min_value=1.0, max_value=9999.0, right_digits=2), 2))
                ),
                status=ProductStatus.active,
            )
        )
    session.add_all(products)
    session.commit()
    session.close()
    return f"Created {count} products"
