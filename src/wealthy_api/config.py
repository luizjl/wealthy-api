from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="WEALTHY_",
        env_file=(".env", ".env.oracle"),
        env_ignore_empty=True,
        extra="ignore",
    )

    database_backend: Literal["sqlite", "oracle"] = "sqlite"
    database_url: str = "sqlite+pysqlite:///./wealthy-dev.db"
    oracle_user: str | None = None
    oracle_password: str | None = None
    oracle_dsn: str = "e7h50o2uobc0nl1q_medium"
    oracle_wallet_location: str | None = None
    oracle_wallet_password: str | None = None
    firebase_project_id: str | None = None
    firebase_credentials_file: str | None = None
    firebase_allowed_uids: str = ""
    firebase_admin_uids: str = ""
    import_max_bytes: int = 100 * 1024 * 1024
    sql_echo: bool = False

    @property
    def allowed_firebase_uids(self) -> frozenset[str]:
        return frozenset(
            uid.strip() for uid in self.firebase_allowed_uids.split(",") if uid.strip()
        )

    @property
    def admin_firebase_uids(self) -> frozenset[str]:
        return frozenset(uid.strip() for uid in self.firebase_admin_uids.split(",") if uid.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()
