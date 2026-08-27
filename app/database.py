import os
from collections.abc import Generator
from functools import lru_cache

from dotenv import load_dotenv
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session


load_dotenv()


class Base(DeclarativeBase):
    """Base class for all database models."""


def create_db_engine() -> Engine:
    """Create a PostgreSQL engine from the configured database URL."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured")

    return create_engine(database_url, pool_pre_ping=True)


@lru_cache
def get_db_engine() -> Engine:
    """Reuse one connection pool for the lifetime of the application."""
    return create_db_engine()


def get_db_session() -> Generator[Session, None, None]:
    """Provide one database session for a request and close it afterward."""
    with Session(get_db_engine()) as session:
        yield session
