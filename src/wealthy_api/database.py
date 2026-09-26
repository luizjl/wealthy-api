from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from wealthy_api.config import get_settings


def create_database_engine(database_url: str, *, echo: bool = False) -> Engine:
    engine_options: dict[str, object] = {"echo": echo, "pool_pre_ping": True}
    if database_url.startswith("sqlite"):
        engine_options["connect_args"] = {"check_same_thread": False}
    return create_engine(database_url, **engine_options)


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    return create_database_engine(settings.database_url, echo=settings.sql_echo)


def get_session() -> Iterator[Session]:
    with Session(get_engine()) as session:
        yield session
