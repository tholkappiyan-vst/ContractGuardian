from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    anthropic_api_key: str
    anthropic_model: str = "claude-sonnet-4-20250514"

    s3_bucket: str = "contractai-documents"
    s3_region: str = "us-east-1"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    s3_endpoint_url: str | None = None

    max_file_size_mb: int = 50
    allowed_file_types: str = "pdf,docx,png,jpg,tiff"

    @property
    def allowed_extensions(self) -> list[str]:
        return self.allowed_file_types.split(",")

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
