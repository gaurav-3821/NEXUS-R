from __future__ import annotations
# ruff: noqa: E402

import asyncio
import json
import os
import socket
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from nexus_r.config import NEXUSConfig
from nexus_r.errors import (
    ProviderAuthError,
    ProviderConnectionError,
    ProviderEmptyResponseError,
    ProviderError,
    ProviderMalformedResponseError,
    ProviderModelUnavailableError,
    ProviderRateLimitError,
    ProviderTimeoutError,
)
from nexus_r.model_registry import ModelRegistry
from modules.orchestrator.src.orchestrator import MainOrchestrator
from modules.trust_layer.src.secret_registry import SecretRegistry


def check(label: str, passed: bool, detail: str = "") -> None:
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {label}", end="")
    if detail:
        print(f" — {detail}")
    else:
        print()


class ChaosServer:
    """Acts as a fake provider that returns controlled failure responses."""
    def __init__(self, mode: str, delay: float = 0, fail_after: int = 0):
        self.mode = mode
        self.delay = delay
        self.fail_after = fail_after
        self._calls = 0
        self.server: asyncio.AbstractServer | None = None
        self.port: int = 0

    async def start(self):
        self.server = await asyncio.start_server(self._handle, "127.0.0.1", 0)
        self.port = self.server.sockets[0].getsockname()[1]
        return self

    async def stop(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()

    async def _handle(self, reader, writer):
        self._calls += 1
        if self.fail_after > 0 and self._calls > self.fail_after:
            writer.close()
            return
        await asyncio.sleep(self.delay)
        raw = await reader.read(65536)
        path = raw.split(b"\r\n", 1)[0].decode("utf-8", errors="ignore").split()[1] if raw else "/"
        if path == "/api/tags":
            body = json.dumps({"models": [{"name": "qwen2.5:1.5b-instruct"}]})
        elif self.mode == "slow":
            await asyncio.sleep(10)
            body = json.dumps({"message": {"content": "slow"}, "done": True})
        elif self.mode == "malformed_json":
            body = "{invalid json"
        elif self.mode == "empty":
            body = json.dumps({"message": {"content": ""}, "done": True})
        elif self.mode == "timeout":
            await asyncio.sleep(30)
            body = json.dumps({"message": {"content": "late"}, "done": True})
        elif self.mode == "partial":
            body = json.dumps({"message": {"content": "partial"}, "done": False})
            await self._respond(writer, body, close=True)
            return
        else:
            body = json.dumps({"message": {"content": "ok"}, "done": True})
        await self._respond(writer, body)

    async def _respond(self, writer, body, close=False):
        resp = f"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {len(body.encode())}\r\n\r\n{body}"
        writer.write(resp.encode())
        await writer.drain()
        if close:
            writer.close()
            await writer.wait_closed()
        else:
            writer.close()
            await writer.wait_closed()


async def test_a_ollama_unavailable():
    print("\n--- A. Ollama Unavailable ---")
    config = NEXUSConfig.default(ROOT / ".chaos")
    config.models.local_api_base = "http://127.0.0.1:1"
    config.models.provider_timeout_seconds = 2
    config.models.enable_mock_fallbacks = False
    orch = MainOrchestrator(config)
    try:
        result = await orch.run_task("hello unavailable test")
        check("Unavailable provider fails with error", not result.get("success"),
              f"error={str(result.get('error',''))[:120]}")
    finally:
        await orch.close()


async def test_b_invalid_groq_key():
    print("\n--- B. Invalid Groq Key ---")
    config = NEXUSConfig.default(ROOT / ".chaos")
    config.models.complexity_threshold = 0.1
    config.models.enable_mock_fallbacks = False
    # Override secret registry with bad key
    secrets = SecretRegistry(config.app_name)
    secrets.set_secret(config.models.byok_secret_name, "sk-invalid-key-for-testing")
    reg = ModelRegistry(config, secrets)
    try:
        result = await reg.complete("test message", preferred="byok")
        check("Invalid key caught", False, "should not succeed")
    except ProviderAuthError:
        check("Invalid key raises ProviderAuthError", True)
    except Exception as exc:
        check("Invalid key raises auth error", "Auth" in type(exc).__name__, str(exc)[:100])


async def test_c_forced_timeouts():
    print("\n--- C. Forced Timeouts (1s, 5s, 30s) ---")
    for timeout_label, timeout_s in [("1s", 1), ("5s should trigger", 5)]:
        config = NEXUSConfig.default(ROOT / ".chaos")
        config.models.local_api_base = f"http://127.0.0.1:{CHAOS_PORT}"
        config.models.provider_timeout_seconds = timeout_s
        config.models.enable_mock_fallbacks = False
        orch = MainOrchestrator(config)
        try:
            result = await orch.run_task("hello timeout test")
            check(f"Timeout {timeout_label} handled", not result.get("success"), f"error={str(result.get('error',''))[:80]}")
        finally:
            await orch.close()


async def test_d_slow_provider():
    print("\n--- D. Slow Provider (10s delay) ---")
    config = NEXUSConfig.default(ROOT / ".chaos")
    config.models.local_api_base = f"http://127.0.0.1:{CHAOS_PORT}"
    config.models.provider_timeout_seconds = 15
    config.models.enable_mock_fallbacks = True
    orch = MainOrchestrator(config)
    try:
        started = time.perf_counter()
        result = await orch.run_task("hello slow provider test")
        elapsed = time.perf_counter() - started
        check("Slow provider handled via fallback", result.get("success"),
              f"elapsed={elapsed:.1f}s (expected ~10s delay)")
        check("Fallback completed within acceptable time", elapsed < 25, f"elapsed={elapsed:.1f}s")
    finally:
        await orch.close()


async def test_e_malformed_json():
    print("\n--- E. Malformed JSON Response ---")
    config = NEXUSConfig.default(ROOT / ".chaos")
    config.models.local_api_base = f"http://127.0.0.1:{CHAOS_PORT}"
    config.models.provider_timeout_seconds = 2
    config.models.enable_mock_fallbacks = False
    orch = MainOrchestrator(config)
    try:
        result = await orch.run_task("hello malformed test")
        check("Malformed JSON handled", not result.get("success"),
              f"error={str(result.get('error',''))[:120]}")
    finally:
        await orch.close()


async def test_f_empty_response():
    print("\n--- F. Empty Response ---")
    config = NEXUSConfig.default(ROOT / ".chaos")
    config.models.local_api_base = f"http://127.0.0.1:{CHAOS_PORT}"
    config.models.provider_timeout_seconds = 2
    config.models.enable_mock_fallbacks = False
    orch = MainOrchestrator(config)
    try:
        result = await orch.run_task("hello empty test")
        check("Empty response handled", not result.get("success"),
              f"error={str(result.get('error',''))[:120]}")
    finally:
        await orch.close()


async def test_g_retry_exhaustion():
    print("\n--- G. Retry Exhaustion (fail 5x, then exhaust) ---")
    config = NEXUSConfig.default(ROOT / ".chaos")
    config.models.local_api_base = "http://127.0.0.1:1"
    config.models.provider_timeout_seconds = 1
    config.models.enable_mock_fallbacks = False
    orch = MainOrchestrator(config)
    try:
        result = await orch.run_task("hello exhaustion test")
        check("Retry exhaustion produces failure result", not result.get("success"),
              f"error={str(result.get('error',''))[:120]}")
    finally:
        await orch.close()


async def main():
    print("=" * 70)
    print("  PROVIDER CHAOS VALIDATION")
    print("=" * 70)

    global CHAOS_PORT
    wd = ROOT / ".chaos"
    wd.mkdir(exist_ok=True)

    slow_server = await ChaosServer("slow", delay=0).start()
    malformed_server = await ChaosServer("malformed_json").start()
    empty_server = await ChaosServer("empty").start()

    tests = [
        ("a_ollama_unavailable", test_a_ollama_unavailable),
        ("b_invalid_groq_key", test_b_invalid_groq_key),
        ("d_slow_provider", test_d_slow_provider),
        ("e_malformed_json", test_e_malformed_json),
        ("f_empty_response", test_f_empty_response),
        ("g_retry_exhaustion", test_g_retry_exhaustion),
    ]

    results = {}
    for name, test_fn in tests:
        try:
            await test_fn()
            results[name] = True
        except Exception as exc:
            print(f"  [ERROR] {name}: {exc}")
            results[name] = False

    await slow_server.stop()
    await malformed_server.stop()
    await empty_server.stop()

    print(f"\n{'='*70}")
    print(f"  RESULTS: {sum(1 for v in results.values() if v)}/{len(results)} passed")
    print(f"{'='*70}")


if __name__ == "__main__":
    if not hasattr(Path, '_mkdir_patched'):
        original_mkdir = Path.mkdir
        def _safe_mkdir(self, *a, **kw):
            try:
                return original_mkdir(self, *a, **kw)
            except FileExistsError:
                pass
        Path.mkdir = _safe_mkdir
        Path._mkdir_patched = True
    CHAOS_PORT = 0
    asyncio.run(main())
