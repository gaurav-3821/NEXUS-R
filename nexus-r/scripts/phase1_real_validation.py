from __future__ import annotations
# ruff: noqa: E402

import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from nexus_r.config import NEXUSConfig
from nexus_r.events import Event
from nexus_r.model_registry import ModelRegistry
from modules.orchestrator.src.orchestrator import MainOrchestrator
from modules.trust_layer.src.secret_registry import SecretRegistry


class FakeOllamaServer:
    def __init__(self, mode: str, model_name: str) -> None:
        self.mode = mode
        self.model_name = model_name
        self.server: asyncio.AbstractServer | None = None
        self.base_url: str | None = None

    async def __aenter__(self) -> "FakeOllamaServer":
        self.server = await asyncio.start_server(self._handle, "127.0.0.1", 0)
        socket = self.server.sockets[0]
        host, port = socket.getsockname()[:2]
        self.base_url = f"http://{host}:{port}"
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self.server is not None:
            self.server.close()
            await self.server.wait_closed()

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        raw = await reader.read(65536)
        request_line = raw.split(b"\r\n", 1)[0].decode("utf-8", errors="ignore")
        parts = request_line.split()
        path = parts[1] if len(parts) >= 2 else "/"
        if path == "/api/tags":
            await self._write_json(writer, {"models": [{"name": self.model_name}]})
            return
        if self.mode == "slow":
            await asyncio.sleep(2.5)
            await self._write_json(
                writer,
                {"message": {"content": "slow response"}, "done": True},
            )
            return
        if self.mode == "malformed":
            await self._write_raw(writer, "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n{")
            return
        if self.mode == "partial_stream":
            body = json.dumps({"message": {"content": "partial "}, "done": False}) + "\n"
            await self._write_raw(
                writer,
                "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n" + body,
                close=True,
            )
            return
        await self._write_json(writer, {"message": {"content": "ok"}, "done": True})

    async def _write_json(self, writer: asyncio.StreamWriter, payload: dict[str, object]) -> None:
        body = json.dumps(payload)
        await self._write_raw(
            writer,
            (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: application/json\r\n"
                f"Content-Length: {len(body.encode('utf-8'))}\r\n"
                "\r\n"
                f"{body}"
            ),
        )

    async def _write_raw(self, writer: asyncio.StreamWriter, payload: str, close: bool = False) -> None:
        writer.write(payload.encode("utf-8"))
        await writer.drain()
        if close:
            writer.close()
            await writer.wait_closed()
            return
        writer.close()
        await writer.wait_closed()


async def run_task_batch(orchestrator: MainOrchestrator, prompts: list[str]) -> dict[str, object]:
    results: list[dict[str, object]] = []
    latencies: list[float] = []
    for prompt in prompts:
        started = time.perf_counter()
        result = await orchestrator.run_task(prompt)
        elapsed_ms = (time.perf_counter() - started) * 1000
        latencies.append(elapsed_ms)
        result["elapsed_ms"] = round(elapsed_ms, 2)
        results.append(result)
    return {
        "results": results,
        "success_rate": round(sum(1 for item in results if item["success"]) / len(results), 3),
        "average_latency_ms": round(sum(latencies) / len(latencies), 2),
        "max_latency_ms": round(max(latencies), 2),
    }


async def test_real_inference(orchestrator: MainOrchestrator) -> dict[str, object]:
    hello = await orchestrator.run_task("hello")
    return {
        "success": hello["success"],
        "routing_model": hello["routing_model"],
        "output_preview": str(hello["output"])[:200],
    }


async def test_streaming(registry: ModelRegistry) -> dict[str, object]:
    chunks: list[str] = []
    model_name = None
    async for chunk in registry.stream("Explain what NEXUS-R is in one short sentence.", preferred="local"):
        if chunk.text:
            chunks.append(chunk.text)
        model_name = chunk.model_name
    return {
        "chunk_count": len(chunks),
        "model_name": model_name,
        "combined_text_preview": "".join(chunks)[:200],
    }


async def test_cancellation(registry: ModelRegistry) -> dict[str, object]:
    async def consume() -> int:
        count = 0
        async for chunk in registry.stream("Repeat the word telemetry many times.", preferred="local"):
            if chunk.text:
                count += 1
                await asyncio.sleep(0.15)
        return count

    task = asyncio.create_task(consume())
    await asyncio.sleep(0.2)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        return {"cancelled": True}
    return {"cancelled": False}


async def test_long_context(orchestrator: MainOrchestrator) -> dict[str, object]:
    prompt = "Summarize this repeated context briefly: " + ("alpha beta gamma delta " * 1500)
    result = await orchestrator.run_task(prompt)
    return {
        "success": result["success"],
        "routing_model": result["routing_model"],
        "output_preview": str(result["output"])[:200],
    }


async def test_sustained_event_logging(orchestrator: MainOrchestrator) -> dict[str, object]:
    prompt = "Explain event sourcing in two short paragraphs. " + ("context " * 1200)
    task = asyncio.create_task(orchestrator.run_task(prompt))
    await asyncio.sleep(0.05)
    pending_before_finish = not task.done()
    mid_events = await orchestrator.event_store.get_by_type("provider_invocation")
    result = await task
    final_events = await orchestrator.event_store.get_by_type("provider_result")
    task_id = result["task_id"]
    return {
        "provider_invocations_during_inference": sum(
            1 for event in mid_events if event.data.get("task_id") == task_id
        ),
        "provider_results_after_completion": sum(
            1 for event in final_events if event.data.get("task_id") == task_id
        ),
        "task_was_still_running_midflight": pending_before_finish,
        "final_success": result["success"],
    }


async def test_fallback_behavior(workspace: Path, config: NEXUSConfig) -> dict[str, object]:
    broken = config.model_copy(deep=True)
    broken.models.local_api_base = "http://127.0.0.1:9"
    broken.models.provider_timeout_seconds = 1
    orchestrator = MainOrchestrator(broken)
    try:
        result = await orchestrator.run_task("hello fallback")
        provider_events = await orchestrator.event_store.get_by_type("provider_result")
        latest_provider = provider_events[-1].data if provider_events else {}
        return {
            "success": result["success"],
            "routing_model": result["routing_model"],
            "provider_model": latest_provider.get("model_name"),
            "provider_used_mock": latest_provider.get("used_mock"),
            "provider_fallback_used": latest_provider.get("fallback_used"),
            "telemetry": orchestrator.get_telemetry_snapshot(),
        }
    finally:
        await orchestrator.close()


async def test_failure_modes(workspace: Path, config: NEXUSConfig) -> dict[str, object]:
    results: dict[str, object] = {}
    fake_base: str

    async with FakeOllamaServer("slow", config.models.local_model.split("/", 1)[-1]) as slow_server:
        slow_config = config.model_copy(deep=True)
        slow_config.models.local_api_base = str(slow_server.base_url)
        slow_config.models.provider_timeout_seconds = 1
        slow_config.models.enable_mock_fallbacks = False
        slow_orchestrator = MainOrchestrator(slow_config)
        try:
            timeout_result = await slow_orchestrator.run_task("hello timeout")
            results["forced_timeout"] = {
                "success": timeout_result["success"],
                "error": timeout_result["error"],
            }
        finally:
            await slow_orchestrator.close()

    async with FakeOllamaServer("malformed", config.models.local_model.split("/", 1)[-1]) as malformed_server:
        malformed_config = config.model_copy(deep=True)
        malformed_config.models.local_api_base = str(malformed_server.base_url)
        malformed_config.models.enable_mock_fallbacks = False
        malformed_orchestrator = MainOrchestrator(malformed_config)
        try:
            malformed_result = await malformed_orchestrator.run_task("hello malformed")
            results["malformed_provider"] = {
                "success": malformed_result["success"],
                "error": malformed_result["error"],
            }
        finally:
            await malformed_orchestrator.close()

    async with FakeOllamaServer("partial_stream", config.models.local_model.split("/", 1)[-1]) as partial_server:
        partial_config = config.model_copy(deep=True)
        partial_config.models.local_api_base = str(partial_server.base_url)
        partial_config.models.enable_mock_fallbacks = False
        partial_orchestrator = MainOrchestrator(partial_config)
        try:
            registry = ModelRegistry(partial_config, partial_orchestrator.secret_registry, telemetry=partial_orchestrator.telemetry)
            try:
                async for _chunk in registry.stream("hello partial", preferred="local"):
                    pass
                results["partial_stream_interruption"] = {"success": True, "error": None}
            except Exception as exc:
                results["partial_stream_interruption"] = {
                    "success": False,
                    "error": str(exc),
                }
        finally:
            await partial_orchestrator.close()

    network_config = config.model_copy(deep=True)
    network_config.models.local_api_base = "http://127.0.0.1:1"
    network_config.models.enable_mock_fallbacks = False
    network_orchestrator = MainOrchestrator(network_config)
    try:
        network_result = await network_orchestrator.run_task("hello network")
        results["network_interruption"] = {
            "success": network_result["success"],
            "error": network_result["error"],
        }
    finally:
        await network_orchestrator.close()

    return results


async def main() -> None:
    workspace = ROOT / ".validation-workspace"
    workspace.mkdir(exist_ok=True)
    (workspace / "src").mkdir(exist_ok=True)
    (workspace / "src" / "sample.py").write_text("print('validate')\n", encoding="utf-8")

    config = NEXUSConfig.default(workspace)
    orchestrator = MainOrchestrator(config)
    try:
        registry = ModelRegistry(config, orchestrator.secret_registry, telemetry=orchestrator.telemetry)
        prompts = [
            "hello",
            "summarize the purpose of this repository",
            "brainstorm a name for a local agent",
            "list all python files",
            "create real_check.txt with content hello",
            "read real_check.txt",
            'find "hello" in "."',
            "create a.txt with content a",
            "create b.txt with content b",
            "create c.txt with content c",
            "list all python files",
            "hello again",
            "draft a short release note",
            "create notes.txt with content release-notes",
            "read notes.txt",
            "brainstorm two test ideas",
            "summarize the current hardening goal",
            "create result.txt with content ok",
            "read result.txt",
            "hello final check",
        ]
        batch = await run_task_batch(orchestrator, prompts)
        output = {
            "real_local_model_available": registry.local.available(),
            "real_byok_key_available": registry.byok.available(),
            "real_inference": await test_real_inference(orchestrator),
            "streaming": await test_streaming(registry),
            "cancellation": await test_cancellation(registry),
            "long_context": await test_long_context(orchestrator),
            "sustained_event_logging": await test_sustained_event_logging(orchestrator),
            "task_batch": batch,
            "cost_summary": await orchestrator.get_cost_summary(),
            "telemetry_snapshot": orchestrator.get_telemetry_snapshot(),
            "fallback_behavior": await test_fallback_behavior(workspace, config),
            "failure_modes": await test_failure_modes(workspace, config),
        }
        print(json.dumps(output, indent=2))
    finally:
        await orchestrator.close()


if __name__ == "__main__":
    asyncio.run(main())
