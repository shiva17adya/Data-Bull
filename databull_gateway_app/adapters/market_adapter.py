"""
Adapter for Member 1 (Market Signal Engine).
Calls Member 1 HTTP service on configured port (e.g., 8001), or falls back to simulated data.
"""

import httpx
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("market_adapter")

class MarketAdapter:
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url.rstrip("/")

    async def fetch_signals(self, symbol: str, lookback: int = 5) -> Optional[Dict[str, Any]]:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.base_url}/signals/{symbol}?lookback={lookback}")
                if res.status_code == 200:
                    return res.json()
        except Exception as e:
            logger.warning(f"Member 1 service unreachable at {self.base_url}: {e}")
        return None
