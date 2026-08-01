"""ChromaDB vector store: one collection per contract for isolation."""
import chromadb
from langchain_chroma import Chroma
from langchain_core.documents import Document
from app.ai_engine.config import get_ai_settings
from app.ai_engine.embeddings import get_embeddings


class ContractVectorStore:
    """Manages per-contract vector collections in ChromaDB."""

    def __init__(self):
        settings = get_ai_settings()
        self._client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        self._embeddings = get_embeddings()
        self._prefix = settings.chroma_collection_prefix

    def _collection_name(self, contract_id: str) -> str:
        # ChromaDB collection names: 3-63 chars, alphanumeric + underscores/hyphens
        clean_id = contract_id.replace("-", "")[:32]
        return f"{self._prefix}_{clean_id}"

    def index_contract(self, contract_id: str, chunks: list[Document]) -> int:
        """Index chunked contract documents. Returns number of chunks stored."""
        collection_name = self._collection_name(contract_id)

        # Delete existing collection if re-indexing
        try:
            self._client.delete_collection(collection_name)
        except ValueError:
            pass

        vectorstore = Chroma(
            collection_name=collection_name,
            embedding_function=self._embeddings,
            client=self._client,
        )

        vectorstore.add_documents(chunks)
        return len(chunks)

    def search(self, contract_id: str, query: str, k: int | None = None) -> list[Document]:
        """Similarity search within a contract's vector store."""
        settings = get_ai_settings()
        k = k or settings.retrieval_top_k
        collection_name = self._collection_name(contract_id)

        vectorstore = Chroma(
            collection_name=collection_name,
            embedding_function=self._embeddings,
            client=self._client,
        )

        return vectorstore.similarity_search(query, k=k)

    def search_with_scores(self, contract_id: str, query: str, k: int | None = None) -> list[tuple[Document, float]]:
        """Search with relevance scores."""
        settings = get_ai_settings()
        k = k or settings.retrieval_top_k
        collection_name = self._collection_name(contract_id)

        vectorstore = Chroma(
            collection_name=collection_name,
            embedding_function=self._embeddings,
            client=self._client,
        )

        return vectorstore.similarity_search_with_relevance_scores(query, k=k)

    def delete_contract(self, contract_id: str):
        """Remove a contract's vector store."""
        collection_name = self._collection_name(contract_id)
        try:
            self._client.delete_collection(collection_name)
        except ValueError:
            pass

    def exists(self, contract_id: str) -> bool:
        """Check if a contract has been indexed."""
        collection_name = self._collection_name(contract_id)
        try:
            col = self._client.get_collection(collection_name)
            return col.count() > 0
        except ValueError:
            return False
