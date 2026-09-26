from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session

from wealthy_api.config import Settings, get_settings


def create_database_engine(
    database_url: str | URL,
    *,
    echo: bool = False,
    connect_args: dict[str, object] | None = None,
) -> Engine:
    engine_options: dict[str, object] = {"echo": echo, "pool_pre_ping": True}
    is_sqlite = str(database_url).startswith("sqlite")
    if is_sqlite:
        engine_options["connect_args"] = {"check_same_thread": False}
    if connect_args:
        engine_options["connect_args"] = connect_args
    engine = create_engine(database_url, **engine_options)
    if is_sqlite:
        event.listen(engine, "connect", _enable_sqlite_foreign_keys)
    return engine


def _enable_sqlite_foreign_keys(connection, _record) -> None:
    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def get_database_url(settings: Settings | None = None) -> str | URL:
    settings = settings or get_settings()
    if settings.database_backend == "sqlite":
        return settings.database_url
    return URL.create("oracle+oracledb")


def get_oracle_connect_args(settings: Settings) -> dict[str, object]:
    required_values = {
        "WEALTHY_ORACLE_USER": settings.oracle_user,
        "WEALTHY_ORACLE_PASSWORD": settings.oracle_password,
        "WEALTHY_ORACLE_WALLET_LOCATION": settings.oracle_wallet_location,
    }
    missing = [name for name, value in required_values.items() if not value]
    if missing:
        raise ValueError(f"Configure as variáveis Oracle obrigatórias: {', '.join(missing)}")

    wallet_path = Path(settings.oracle_wallet_location or "").expanduser()
    if not wallet_path.is_dir():
        raise ValueError(
            "WEALTHY_ORACLE_WALLET_LOCATION deve apontar para a pasta extraída da wallet"
        )
    missing_wallet_files = [
        filename
        for filename in ("tnsnames.ora", "ewallet.pem")
        if not (wallet_path / filename).is_file()
    ]
    if missing_wallet_files:
        missing_files = ", ".join(missing_wallet_files)
        raise ValueError(f"A pasta da wallet precisa conter: {missing_files}")

    connect_args: dict[str, object] = {
        "user": settings.oracle_user,
        "password": settings.oracle_password,
        "dsn": settings.oracle_dsn,
        "config_dir": str(wallet_path),
        "wallet_location": str(wallet_path),
    }
    if settings.oracle_wallet_password:
        connect_args["wallet_password"] = settings.oracle_wallet_password
    return connect_args


def create_configured_database_engine(settings: Settings | None = None) -> Engine:
    settings = settings or get_settings()
    connect_args: dict[str, object] | None = None
    if settings.database_backend == "oracle":
        connect_args = get_oracle_connect_args(settings)

    return create_database_engine(
        get_database_url(settings),
        echo=settings.sql_echo,
        connect_args=connect_args,
    )


@lru_cache
def get_engine() -> Engine:
    return create_configured_database_engine()


def get_session() -> Iterator[Session]:
    with Session(get_engine()) as session:
        yield session
