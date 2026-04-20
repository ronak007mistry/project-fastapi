import csv
from contextlib import asynccontextmanager
from datetime import datetime
from decimal import Decimal
from io import BytesIO, StringIO
from typing import Annotated

from celery.result import AsyncResult
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlmodel import Session, select
from sqlalchemy import or_

from auth import verify_token
from celery_app import celery_app
from db import create_db_and_tables, get_session
from encrypt_middleware import EncryptJsonMiddleware
from models import Category, Product, ProductStatus
from tasks import generate_products

SessionDep = Annotated[Session, Depends(get_session)]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(title="Products service", lifespan=lifespan)
app.add_middleware(EncryptJsonMiddleware)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "products_engine"}


@app.post("/categories/", dependencies=[Depends(verify_token)])
def create_category(category: Category, session: SessionDep) -> Category:
    session.add(category)
    session.commit()
    session.refresh(category)
    return category


@app.post("/products/", dependencies=[Depends(verify_token)])
def create_product(product: Product, session: SessionDep) -> Product:
    category = session.get(Category, product.category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    product.updated_at = datetime.utcnow()
    session.add(product)
    session.commit()
    session.refresh(product)
    return product


@app.get("/products/", dependencies=[Depends(verify_token)])
def read_products(
    session: SessionDep,
    offset: int = 0,
    limit: Annotated[int, Query(le=500)] = 100,
) -> list[Product]:
    return list(session.exec(select(Product).offset(offset).limit(limit)).all())


@app.get("/products/search", dependencies=[Depends(verify_token)])
def search_products(
    session: SessionDep,
    q: str = Query(min_length=1),
    offset: int = 0,
    limit: Annotated[int, Query(le=500)] = 100,
) -> list[Product]:
    pattern = f"%{q}%"
    stmt = (
        select(Product)
        .where(
            or_(
                Product.title.ilike(pattern),
                Product.description.ilike(pattern),
            )
        )
        .offset(offset)
        .limit(limit)
    )
    return list(session.exec(stmt).all())


@app.get("/products/{product_id}", dependencies=[Depends(verify_token)])
def read_product(product_id: int, session: SessionDep) -> Product:
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@app.put("/products/{product_id}", dependencies=[Depends(verify_token)])
def update_product(product_id: int, data: Product, session: SessionDep) -> Product:
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    product.title = data.title.strip()
    product.description = data.description
    product.price = Decimal(str(data.price))
    product.status = data.status
    product.category_id = data.category_id
    product.updated_at = datetime.utcnow()

    session.add(product)
    session.commit()
    session.refresh(product)
    return product


@app.delete("/products/{product_id}", dependencies=[Depends(verify_token)])
def delete_product(product_id: int, session: SessionDep) -> dict:
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    session.delete(product)
    session.commit()
    return {"ok": True, "message": "Product deleted"}


@app.post("/products/bulk", dependencies=[Depends(verify_token)])
def bulk_create_products(
    session: SessionDep,
    count: int = Query(..., ge=1, le=50_000),
    category_id: int = Query(...),
) -> dict:
    if not session.get(Category, category_id):
        raise HTTPException(status_code=404, detail="Category not found")
    task = generate_products.delay(count=count, category_id=category_id)
    return {"message": "Bulk product creation started", "task_id": task.id}


@app.get("/tasks/{task_id}", dependencies=[Depends(verify_token)])
def get_task_status(task_id: str) -> dict:
    task = AsyncResult(task_id, app=celery_app)
    return {"task_id": task_id, "status": task.status, "result": task.result}
