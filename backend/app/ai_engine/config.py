from pydantic_settings import BaseSettings
from functools import lru_cache


class AIEngineSettings(BaseSettings):
    gemini_api_key: str
    gemini_model: str = "gemini-flash-latest"
    gemini_embedding_model: str = "models/text-embedding-004"

    chroma_persist_dir: str = "./data/vectorstore"
    chroma_collection_prefix: str = "contract"

    chunk_size: int = 1000
    chunk_overlap: int = 200
    retrieval_top_k: int = 8

    max_retries: int = 6
    request_timeout: int = 120

    class Config:
        env_file = ".env"
        env_prefix = ""


@lru_cache
def get_ai_settings() -> AIEngineSettings:
    return AIEngineSettings()
