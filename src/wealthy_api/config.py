from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="WEALTHY_", env_file=".env", extra="ignore")

    database_url: str = "sqlite+pysqlite:///./wealthy-dev.db"
    firebase_project_id: str | None = None
    firebase_allowed_uids: str = ""
    sql_echo: bool = False

    @property
    def allowed_firebase_uids(self) -> frozenset[str]:
        return frozenset(
            uid.strip() for uid in self.firebase_allowed_uids.split(",") if uid.strip()
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
