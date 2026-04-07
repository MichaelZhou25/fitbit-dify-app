from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db import base  # noqa: F401
from app.models.base import Base

settings = get_settings()


def engine_kwargs_for_database_url(database_url: str) -> dict:
    normalized = database_url.lower()
    if normalized.startswith("sqlite"):
        return {
            "connect_args": {"check_same_thread": False},
        }
    if normalized.startswith("postgresql"):
        return {
            "pool_pre_ping": True,
            "pool_recycle": 1800,
        }
    return {}


def build_engine(database_url: str):
    return create_engine(database_url, **engine_kwargs_for_database_url(database_url))


engine = build_engine(settings.resolved_database_url)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=Session)


def create_db_and_tables() -> None:
    Base.metadata.create_all(bind=engine)
