import logging
from typing import Any

logger = logging.getLogger(__name__)

class VisionProcessor:
    """Lightweight model capability checker — knows if a model supports vision natively."""

    async def is_native_vlm(self, model_name: str, openrouter_models: list[dict[str, Any]] | None = None) -> bool:
        """Check if model is a native VLM via OpenRouter modality data or keyword fallback."""
        if openrouter_models:
            for model in openrouter_models:
                if model.get("id") == model_name or model.get("name") == model_name:
                    return model.get("architecture", "") == "text+image->text"
        vlm_keywords = ["vl", "vision", "llava", "bakllava", "moondream",
                        "qwen-vl", "qwen2-vl", "qwen2.5-vl",
                        "gpt-4o", "claude-3.5-sonnet", "gemini-1.5", "pixtral"]
        name = model_name.lower()
        return any(kw in name for kw in vlm_keywords)
