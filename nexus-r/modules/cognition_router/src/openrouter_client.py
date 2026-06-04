import httpx
import logging
from typing import Any

logger = logging.getLogger("nexus-r.openrouter_client")

class OpenRouterClient:
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.base_url = "https://openrouter.ai/api/v1/models"

    async def list_models(self) -> list[dict[str, Any]]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(self.base_url)
                resp.raise_for_status()
                data = resp.json()
                results = []
                for item in data.get("data", []):
                    pricing = item.get("pricing", {})
                    # Parse prompt and completion prices as floats
                    try:
                        prompt_price = float(pricing.get("prompt") or 0)
                        completion_price = float(pricing.get("completion") or 0)
                    except (ValueError, TypeError):
                        prompt_price = -1.0
                        completion_price = -1.0
                        
                    # Only add the model if it is completely free
                    if prompt_price == 0.0 and completion_price == 0.0:
                        results.append({
                            "id": item.get("id"),
                            "name": item.get("name"),
                            "created": item.get("created"),
                            "description": (item.get("description") or "")[:300],
                            "pricing": pricing,
                            "context_length": item.get("context_length"),
                            "architecture": item.get("architecture", {}).get("modality", "text"),
                        })
                return results
        except Exception as e:
            logger.error("Failed to fetch OpenRouter models: %s", e)
            return []
