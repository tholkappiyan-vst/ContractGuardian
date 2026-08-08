from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    upload_dir: str = "./data/uploads"

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
