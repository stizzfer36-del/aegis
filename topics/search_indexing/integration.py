"""Search / Indexing — MeiliSearch / Typesense / OpenSearch integrations."""
from __future__ import annotations
import os


class SearchIndexingTopic:
    name = "search_indexing"
    tools = ["meilisearch", "typesense", "opensearch", "elasticsearch", "manticore", "quickwit", "tantivy"]

    async def meilisearch_index(self, index: str, documents: list) -> dict:
        url = os.getenv("MEILI_URL", "http://localhost:7700")
        key = os.getenv("MEILI_KEY", "")
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.post(f"{url}/indexes/{index}/documents",
                                  headers={"Authorization": f"Bearer {key}"},
                                  json=documents)
                return r.json()
        except Exception as e:
            return {"error": str(e)}
