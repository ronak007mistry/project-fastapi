import os

from celery import Celery
from sqlmodel import Session

from db import engine

_redis = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "worker",
    broker=_redis,
    backend=_redis,
)


def get_db_session() -> Session:
    return Session(engine)


import tasks  # noqa: E402,F401 — register Celery task definitions
from db import create_db_and_tables

create_db_and_tables()
