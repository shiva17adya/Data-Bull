"""
Adapter for Member 2 (Financial Document RAG).
Calls Member 2 HTTP service on configured port (e.g., 8002), preserving full 9-field attribution.
"""

import httpx
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("rag_adapter")

class RAGAdapter:
    def __init__(self, base_url: str = "http://localhost:8002"):
        self.base_url = base_url.rstrip("/")

    async def retrieve(self, query: str, symbol: Optional[str] = None, top_k: int = 5) -> Optional[Dict[str, Any]]:
        try:
            payload = {"query": query, "symbol": symbol, "top_k": top_k}
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.post(f"{self.base_url}/retrieve", json=payload)
                if res.status_code == 200:
                    return res.json()
        except Exception as e:
            logger.warning(f"Member 2 service unreachable at {self.base_url}: {e}")
        return None
