from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from nexus_r.config import NEXUSConfig
from nexus_r.errors import ProviderConnectionError, ProviderAuthError
from modules.orchestrator.src.orchestrator import MainOrchestrator


ROOT = Path(__file__).resolve().parents[2]


async def _run_and_close(cfg: NEXUSConfig, task: str) -> dict:
    orch = MainOrchestrator(cfg)
    try:
        return await orch.run_task(task)
    finally:
        await orch.close()


@pytest.mark.asyncio
async def test_ollama_unavailable_uses_mock_fallback() -> None:
    wd = ROOT / ".phase-c-test" / "provider-unavailable"
    wd.mkdir(parents=True, exist_ok=True)
    config = NEXUSConfig.default(wd)
    config.models.local_api_base = "http://127.0.0.1:1"
    config.models.enable_mock_fallbacks = True
    result = await _run_and_close(config, "hello")
    assert result.get("success") is True, f"Should fall back to mock, got: {result}"
    assert result.get("routing_model") is not None, "Mock fallback should have a routing model"


@pytest.mark.asyncio
async def test_invalid_byok_key_uses_local_mock() -> None:
    wd = ROOT / ".phase-c-test" / "invalid-key"
    wd.mkdir(parents=True, exist_ok=True)
    import os
    old = os.environ.pop("NEXUS_BYOK_API_KEY", None)
    try:
        config = NEXUSConfig.default(wd)
        config.models.byok_api_key_env = "NEXUS_BYOK_API_KEY"
        config.models.enable_mock_fallbacks = True
        result = await _run_and_close(config, "explain SQL in one sentence")
        assert result.get("success") is True, f"Should use mock fallback: {result}"
        assert result.get("routing_model") is not None, "Should have a routing model"
    finally:
        if old is not None:
            os.environ["NEXUS_BYOK_API_KEY"] = old


@pytest.mark.asyncio
async def test_fast_timeout_does_not_crash() -> None:
    wd = ROOT / ".phase-c-test" / "timeout"
    wd.mkdir(parents=True, exist_ok=True)
    config = NEXUSConfig.default(wd)
    config.models.provider_timeout_seconds = 1
    config.models.enable_mock_fallbacks = True
    result = await _run_and_close(config, "hello")
    assert result.get("success") is True, f"Should not crash: {result}"


@pytest.mark.asyncio
async def test_retry_exhaustion_raises_eventually() -> None:
    wd = ROOT / ".phase-c-test" / "retry-exhaust"
    wd.mkdir(parents=True, exist_ok=True)
    config = NEXUSConfig.default(wd)
    config.models.local_api_base = "http://127.0.0.1:1"
    config.models.enable_mock_fallbacks = True
    config.models.provider_timeout_seconds = 1
    result = await _run_and_close(config, "hello")
    assert result.get("success") is True
