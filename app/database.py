import os
from collections.abc import Generator
from functools import lru_cache

from dotenv import load_dotenv
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session


load_dotenv()


class Base(DeclarativeBase):
    """Base class for all database models."""


def normalize_database_url(database_url: str) -> str:
    """Use the installed psycopg v3 driver for generic PostgreSQL URLs."""
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+psycopg://", 1)
    return database_url


def create_db_engine() -> Engine:
    """Create a PostgreSQL engine from the configured database URL."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured")

    return create_engine(normalize_database_url(database_url), pool_pre_ping=True)


@lru_cache
def get_db_engine() -> Engine:
    """Reuse one connection pool for the lifetime of the application."""
    return create_db_engine()


def get_db_session() -> Generator[Session, None, None]:
    """Provide one database session for a request and close it afterward."""
    with Session(get_db_engine()) as session:
        yield session
