"""
Adapter for Member 3 (User Profile & Portfolio Service).
Calls Member 3 HTTP service on configured port (e.g., 8003).
"""

import httpx
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("profile_adapter")

class ProfileAdapter:
    def __init__(self, base_url: str = "http://localhost:8003"):
        self.base_url = base_url.rstrip("/")

    async def fetch_personalization(self, user_id: str, symbol: str) -> Optional[Dict[str, Any]]:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.base_url}/users/{user_id}/personalization/{symbol}")
                if res.status_code == 200:
                    return res.json()
        except Exception as e:
            logger.warning(f"Member 3 service unreachable at {self.base_url}: {e}")
        return None

    async def fetch_portfolio(self, user_id: str) -> Optional[Dict[str, Any]]:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.base_url}/users/{user_id}/portfolio")
                if res.status_code == 200:
                    return res.json()
        except Exception as e:
            logger.warning(f"Member 3 portfolio service unreachable: {e}")
        return None
