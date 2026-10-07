from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "TenderIQ Iraq"
    app_env: str = "development"
    debug: bool = True
    secret_key: str = "dev-secret-change-me"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14

    database_url: str = "sqlite:///./data/tenderiq.db"
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "tenderiq"
    minio_secret_key: str = "tenderiqsecret"
    minio_bucket: str = "tenderiq"
    minio_secure: bool = False

    cors_origins: str = "http://localhost:8000"

    # Local in-process crawl schedule (works without Redis/Celery)
    crawl_scheduler_enabled: bool = True
    crawl_interval_minutes: int = 60
    crawl_scheduler_initial_delay_seconds: int = 45

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
