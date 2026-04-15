"""Vector Search — Qdrant / Faiss / LanceDB integrations."""
from __future__ import annotations
from typing import List


class VectorSearchTopic:
    name = "vector_search"
    tools = ["qdrant", "milvus", "faiss", "lancedb", "pgvector"]

    async def qdrant_search(self, collection: str, vector: List[float], top_k: int = 5) -> list:
        try:
            from qdrant_client import QdrantClient
            client = QdrantClient(":memory:")
            results = client.search(collection_name=collection, query_vector=vector, limit=top_k)
            return [r.dict() for r in results]
        except ImportError:
            return [{"error": "qdrant-client not installed"}]
