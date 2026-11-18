from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: str = ""
    admin_ids: str = ""
    database_url: str = "sqlite+aiosqlite:///./movieuz.db"
    redis_url: str = ""
    omdb_api_key: str = ""

    log_level: str = "INFO"
    page_size: int = 5
    request_timeout: float = 10.0
    max_retries: int = 2
    cache_ttl: int = 600

    @property
    def admin_id_list(self) -> list[int]:
        result: list[int] = []
        for part in self.admin_ids.replace(",", " ").replace(";", " ").split():
            try:
                result.append(int(part))
            except ValueError:
                continue
        return result

    @property
    def is_configured(self) -> bool:
        return bool(self.bot_token)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
