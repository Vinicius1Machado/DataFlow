from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Data Script Generator API"
    app_version: str = "0.1.0"
    app_env: str = "local"
    api_v1_prefix: str = "/api/v1"

    backend_port: int = 8000
    backend_url: str = "http://localhost:8000"
    backend_cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    next_public_api_url: str = "http://localhost:8000"

    postgres_db: str = "data_script_generator"
    postgres_user: str
    postgres_password: str
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    database_url: str | None = None

    minio_root_user: str
    minio_root_password: str
    minio_bucket: str = "data-generator"
    minio_endpoint: str = "http://localhost:9000"
    minio_public_endpoint: str = "http://localhost:9000"
    minio_worker_endpoint: str | None = None
    minio_region: str = "us-east-1"

    n8n_port: int = 5678
    n8n_basic_auth_user: str
    n8n_basic_auth_password: str
    n8n_webhook_url: str = "http://n8n:5678/webhook/data-analysis"
    n8n_callback_url: str = "http://backend:8000/api/n8n/callback"
    backend_callback_url: str = "http://backend:8000/api/n8n/callback"
    worker_profile_url: str = "http://worker:8001/profile"
    n8n_webhook_secret: str

    ai_provider: str = "openai"
    openai_api_key: str

    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("backend_cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url:
            return self.database_url

        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def is_local_environment(self) -> bool:
        return self.app_env.lower() in {"local", "dev", "development"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
