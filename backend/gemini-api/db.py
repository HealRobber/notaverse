from typing import Generator, AsyncGenerator, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)

from settings import settings


Base = declarative_base()

# ----- Sync -----
_sync_engine = None
_SessionLocal: Optional[sessionmaker] = None


def get_sync_engine():
    global _sync_engine
    if _sync_engine is None:
        _sync_engine = create_engine(settings.database_url_sync, **settings.sync_engine_kwargs())
    return _sync_engine


def get_session_factory() -> sessionmaker:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=get_sync_engine(),
            autocommit=False,
            autoflush=False,
            future=True,
        )
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    # 모델 import 이후 호출 필요
    from . import models  # noqa: F401
    engine = get_sync_engine()
    Base.metadata.create_all(bind=engine)


# ----- Async -----
_async_engine = None
_AsyncSessionLocal: Optional[async_sessionmaker[AsyncSession]] = None


def get_async_engine():
    global _async_engine
    if _async_engine is None:
        _async_engine = create_async_engine(settings.database_url_async, **settings.async_engine_kwargs())
    return _async_engine


def get_async_session_factory() -> async_sessionmaker[AsyncSession]:
    global _AsyncSessionLocal
    if _AsyncSessionLocal is None:
        _AsyncSessionLocal = async_sessionmaker(
            bind=get_async_engine(),
            expire_on_commit=False,
            class_=AsyncSession,
        )
    return _AsyncSessionLocal


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    AsyncSessionLocal = get_async_session_factory()
    async with AsyncSessionLocal() as session:
        yield session
