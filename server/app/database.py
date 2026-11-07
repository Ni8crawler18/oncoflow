"""Database engine, session factory and FastAPI dependency."""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

from .config import settings

db_url = settings.normalized_database_url
connect_args = {}
if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

# pool_pre_ping keeps connections healthy on managed hosts (Render) that drop
# idle connections.
engine = create_engine(
    db_url, connect_args=connect_args, pool_pre_ping=True, future=True
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
