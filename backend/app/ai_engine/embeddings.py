"""Embedding generation using Google Gemini text-embedding-004."""
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from app.ai_engine.config import get_ai_settings


def get_embeddings() -> GoogleGenerativeAIEmbeddings:
    """Get configured Gemini embedding model."""
    settings = get_ai_settings()
    return GoogleGenerativeAIEmbeddings(
        model=settings.gemini_embedding_model,
        google_api_key=settings.gemini_api_key,
        task_type="retrieval_document",
    )


def get_query_embeddings() -> GoogleGenerativeAIEmbeddings:
    """Get embedding model configured for queries (retrieval_query task type)."""
    settings = get_ai_settings()
    return GoogleGenerativeAIEmbeddings(
        model=settings.gemini_embedding_model,
        google_api_key=settings.gemini_api_key,
        task_type="retrieval_query",
    )
