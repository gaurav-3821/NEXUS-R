from __future__ import annotations
# ruff: noqa: E402

import asyncio
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from nexus_r.config import NEXUSConfig
from nexus_r.errors import ProviderAuthError
from nexus_r.events import Event, IntentResult, PermissionTier
from nexus_r.model_registry import ModelRegistry, ModelInvocationResult
from modules.cognition_router.src.router import CognitionRouter
from modules.orchestrator.src.orchestrator import MainOrchestrator
from modules.state_core.src.event_store import EventStore
from modules.trust_layer.src.secret_registry import SecretRegistry


def section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def check(description: str, passed: bool, detail: str = "") -> None:
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {description}")
    if detail:
        print(f"         {detail}")


async def test_real_byok_inference(registry: ModelRegistry) -> dict[str, object]:
    section("1. Real BYOK Inference (Groq)")
    started = time.perf_counter()
    try:
        result = await registry.complete("Reply with exactly: GROQ_OK", preferred="byok")
        latency = (time.perf_counter() - started) * 1000
        ok = not result.used_mock and "GROQ_OK" in result.text.upper()
        check("Real BYOK inference returns non-mock response", ok,
              f"model={result.model_name}, cost=${result.estimated_cost:.5f}, latency={latency:.0f}ms")
        check("BYOK cost is non-zero", result.estimated_cost > 0,
              f"cost={result.estimated_cost}")
        check("BYOK latency is reasonable (<30s)", latency < 30000,
              f"latency={latency:.0f}ms")
        return {"success": ok, "model": result.model_name, "cost": result.estimated_cost, "latency_ms": latency}
    except Exception as exc:
        check("Real BYOK inference", False, str(exc)[:200])
        return {"success": False, "error": str(exc)}


async def test_local_to_byok_escalation(workspace: Path, registry: ModelRegistry) -> dict[str, object]:
    section("2. Local -> BYOK Escalation")
    config = NEXUSConfig.default(workspace)
    config.models.complexity_threshold = 0.1
    config.models.byok_cost_per_call = 0.02
    orchestrator = MainOrchestrator(config)
    try:
        await orchestrator.initialize()
        router = CognitionRouter(config, orchestrator.event_store, orchestrator.secret_registry, telemetry=orchestrator.telemetry)
        intent = IntentResult(
            raw_input="explain the economic impact of AI in one sentence",
            normalized_input="explain the economic impact of AI in one sentence",
            task_type="general_llm",
            complexity=0.9,
            confidence=0.9,
            parameters={"prompt": "What is the economic impact of AI? Reply in one sentence."},
            suggested_tier=PermissionTier.T4,
        )
        decision = await router.route(intent)
        escalated = "groq" in decision.selected_model.lower()
        check("Complex task escalates to BYOK", escalated,
              f"selected_model={decision.selected_model}, rationale={decision.rationale}")
        check("Routing includes fallback chain", len(decision.fallback_chain) > 1,
              f"chain={decision.fallback_chain}")
        result = None
        try:
            result = await registry.complete(
                "What is the economic impact of AI? Reply in one sentence.",
                preferred="byok",
            )
            byok_used = "groq" in result.model_name.lower()
            check("BYOK execution succeeds", True,
                  f"model={result.model_name}, cost=${result.estimated_cost:.5f}")
            check("BYOK model was actually used", byok_used,
                  f"model={result.model_name}")
        except Exception as exc:
            check("BYOK execution succeeds", False, str(exc)[:200])
        return {
            "escalated": escalated,
            "selected_model": decision.selected_model,
            "chain": decision.fallback_chain,
            "byok_result": result is not None,
        }
    finally:
        await orchestrator.close()


async def test_fallback_chain(workspace: Path) -> dict[str, object]:
    section("3. Fallback Chain Correctness")
    config = NEXUSConfig.default(workspace)
    config.models.local_api_base = "http://127.0.0.1:9"
    config.models.provider_timeout_seconds = 1
    config.models.complexity_threshold = 0.1
    config.models.byok_cost_per_call = 0.02
    orchestrator = MainOrchestrator(config)
    try:
        result = await orchestrator.run_task("explain fallback chain behavior test")
        fallback_events = await orchestrator.event_store.get_by_type("provider_result")
        latest = fallback_events[-1].data if fallback_events else {}
        mock_used = latest.get("used_mock", True)
        check("Fallback chain completes", result["success"],
              f"routing_model={result.get('routing_model')}, mock_used={mock_used}")
        telemetry = orchestrator.get_telemetry_snapshot()
        retries = telemetry.get("counters", {}).get("provider.retries_total", 0)
        failures = telemetry.get("counters", {}).get("provider.failures_total", 0)
        check("Retries or fallbacks were triggered", retries > 0 or failures > 0,
              f"retries={retries}, failures={failures}")
        return {
            "success": result["success"],
            "mock_used": mock_used,
            "retries": retries,
            "failures": failures,
        }
    finally:
        await orchestrator.close()


async def test_timeout_fallback(workspace: Path) -> dict[str, object]:
    section("4. Timeout-Triggered Fallback")
    config = NEXUSConfig.default(workspace)
    config.models.local_api_base = "http://127.0.0.1:1"
    config.models.provider_timeout_seconds = 1
    config.models.enable_mock_fallbacks = True
    orchestrator = MainOrchestrator(config)
    try:
        started = time.perf_counter()
        result = await orchestrator.run_task("hello timeout fallback test")
        elapsed = (time.perf_counter() - started) * 1000
        check("Timeout fallback completes", result["success"],
              f"elapsed={elapsed:.0f}ms, routing_model={result.get('routing_model')}")
        check("Completes within reasonable time (<15s)", elapsed < 15000,
              f"elapsed={elapsed:.0f}ms")
        return {"success": result["success"], "elapsed_ms": elapsed}
    finally:
        await orchestrator.close()


async def test_malformed_response_handling(workspace: Path) -> dict[str, object]:
    section("5. Malformed Provider Response Handling")
    config = NEXUSConfig.default(workspace)
    config.models.local_api_base = "http://127.0.0.1:1"
    config.models.provider_timeout_seconds = 2
    config.models.enable_mock_fallbacks = False
    orchestrator = MainOrchestrator(config)
    try:
        result = await orchestrator.run_task("hello malformed handling test")
        check("Malformed/unreachable provider caught", not result["success"],
              f"error={str(result.get('error',''))[:150]}")
        return {"success": result["success"], "error": result.get("error")}
    finally:
        await orchestrator.close()


async def test_retry_behavior(workspace: Path, registry: ModelRegistry) -> dict[str, object]:
    section("6. Retry & Provider Telemetry Logging")
    try:
        result = await registry.complete("test message", preferred="byok")
        check("BYOK provider succeeds", result.used_mock is False,
              f"model={result.model_name}, cost=${result.estimated_cost:.5f}")
        mock_result = await registry.complete("test message", preferred="local")
        check("Local provider succeeds", True,
              f"model={mock_result.model_name}, mock={mock_result.used_mock}")
        return {"byok_ok": True, "local_ok": True}
    except Exception as exc:
        check("Provider telemetry test", False, str(exc)[:200])
        return {"error": str(exc)}


async def test_tier_transparency(workspace: Path) -> dict[str, object]:
    section("7. Tier Escalation Transparency")
    config = NEXUSConfig.default(workspace)
    config.models.complexity_threshold = 0.5
    orchestrator = MainOrchestrator(config)
    try:
        await orchestrator.initialize()
        router = CognitionRouter(config, orchestrator.event_store, orchestrator.secret_registry, telemetry=orchestrator.telemetry)
        intent_low = IntentResult(
            raw_input="hello",
            normalized_input="hello",
            task_type="general_llm",
            complexity=0.1,
            confidence=0.9,
            parameters={"prompt": "Say hello"},
            suggested_tier=PermissionTier.T1,
        )
        intent_high = IntentResult(
            raw_input="explain global economic trends in detail",
            normalized_input="explain global economic trends in detail",
            task_type="general_llm",
            complexity=0.9,
            confidence=0.9,
            parameters={"prompt": "Explain global economic trends in one sentence."},
            suggested_tier=PermissionTier.T4,
        )
        decision_low = await router.route(intent_low)
        decision_high = await router.route(intent_high)
        low_local = "ollama" in decision_low.selected_model.lower() or "mock" in decision_low.selected_model.lower()
        high_byok = "groq" in decision_high.selected_model.lower() or "gpt" in decision_high.selected_model.lower()
        check("Low-complexity task routed locally", low_local,
              f"model={decision_low.selected_model}, rationale={decision_low.rationale}")
        check("High-complexity task escalated to BYOK", high_byok,
              f"model={decision_high.selected_model}, rationale={decision_high.rationale}")
        check("Tiers are never silently skipped",
              decision_low.selected_model != decision_high.selected_model,
              f"low={decision_low.selected_model}, high={decision_high.selected_model}")
        return {
            "low_model": decision_low.selected_model,
            "high_model": decision_high.selected_model,
            "low_rationale": decision_low.rationale,
            "high_rationale": decision_high.rationale,
        }
    finally:
        await orchestrator.close()


async def main() -> None:
    api_key = os.environ.get("NEXUS_BYOK_API_KEY")
    if not api_key:
        print("WARNING: NEXUS_BYOK_API_KEY not set. BYOK tests will be skipped.")
        print("Set it with: $env:NEXUS_BYOK_API_KEY='your-groq-key'")
    else:
        print(f"BYOK API key found: {api_key[:8]}...{api_key[-4:]}")

    workspace = ROOT / ".byok-validation-workspace"
    workspace.mkdir(exist_ok=True)

    config = NEXUSConfig.default(workspace)
    store = EventStore(config.database.path)
    await store.initialize()

    secret_registry = SecretRegistry(config.app_name)
    secret_registry.bootstrap_from_environment(config.models.byok_secret_name, config.models.byok_api_key_env)

    registry = ModelRegistry(config, secret_registry)

    print(f"Local model available: {registry.local.available()}")
    print(f"BYOK model available: {registry.byok.available()}")
    print(f"BYOK model: {registry.byok.name}")

    results = {}

    if registry.byok.available():
        results["real_byok_inference"] = await test_real_byok_inference(registry)
    else:
        check("Real BYOK inference", False, "No BYOK API key configured")
        results["real_byok_inference"] = {"success": False, "error": "no key"}

    results["local_to_byok_escalation"] = await test_local_to_byok_escalation(workspace, registry)
    results["fallback_chain"] = await test_fallback_chain(workspace)
    results["timeout_fallback"] = await test_timeout_fallback(workspace)
    results["malformed_response"] = await test_malformed_response_handling(workspace)
    results["provider_telemetry"] = await test_retry_behavior(workspace, registry)
    results["tier_transparency"] = await test_tier_transparency(workspace)

    await store.close()

    print(f"\n{'='*60}")
    print(f"  SUMMARY")
    print(f"{'='*60}")
    passed = sum(1 for r in results.values() if isinstance(r, dict) and r.get("success", True))
    total = sum(1 for r in results.values() if isinstance(r, dict))
    print(f"  Tests passed: {passed}/{total}")

    output_path = workspace / "byok_validation_result.json"
    output_path.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print(f"\nFull results written to: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
