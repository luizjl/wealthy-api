from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session

from wealthy_api.config import Settings, get_settings


def get_database_url() -> URL:
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
    return create_engine(
        get_database_url(),
        echo=settings.sql_echo,
        pool_pre_ping=True,
        connect_args=get_oracle_connect_args(settings),
    )


@lru_cache
def get_engine() -> Engine:
    return create_configured_database_engine()


def get_session() -> Iterator[Session]:
    with Session(get_engine()) as session:
        yield session
