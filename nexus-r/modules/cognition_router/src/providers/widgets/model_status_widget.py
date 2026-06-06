import httpx
import logging
from ..widget_provider import WidgetProvider, WidgetResult

logger = logging.getLogger("nexus-r.model_status_widget")

OLLAMA_KEYWORDS = ["ollama", "local model", "model status", "available models"]

class ModelStatusWidget(WidgetProvider):
    async def should_run(self, context) -> bool:
        query = getattr(context, "raw_input", "") or ""
        return any(kw in query.lower() for kw in OLLAMA_KEYWORDS)

    async def execute(self, context) -> WidgetResult | None:
        local = await self._check_ollama()
        return WidgetResult(
            widget_type="model_status",
            data={
                "local_available": local is not None,
                "local_models": local or [],
                "ollama_running": local is not None,
            },
            title="Model Status",
            priority=8,
        )

    async def _check_ollama(self) -> list[str] | None:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get("http://127.0.0.1:11434/api/tags")
                resp.raise_for_status()
                data = resp.json()
                if not isinstance(data, dict):
                    return None
                models = data.get("models") or data.get("models_list") or []
                if not isinstance(models, list):
                    return None
                return [m.get("name", "unknown") for m in models if isinstance(m, dict)]
        except Exception:
            return None
