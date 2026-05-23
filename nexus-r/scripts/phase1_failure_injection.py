from __future__ import annotations
# ruff: noqa: E402

import asyncio
import json
import os
import sqlite3
import sys
from pathlib import Path

from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cryptography.fernet import InvalidToken

from nexus_r.config import NEXUSConfig
from nexus_r.events import Event
from modules.orchestrator.src.orchestrator import MainOrchestrator
from modules.state_core.src.identity_store import IdentityStore


async def inject_failures(workspace: Path) -> dict[str, dict[str, object]]:
    config = NEXUSConfig.default(workspace)
    orchestrator = MainOrchestrator(config)
    await orchestrator.initialize()
    results: dict[str, dict[str, object]] = {}

    try:
        os.environ["NEXUS_SANDBOX__COMMAND_TIMEOUT_SECONDS"] = "not-an-int"
        NEXUSConfig.from_env(workspace)
        results["invalid_config"] = {"passed": False, "reason": "Expected validation error."}
    except ValidationError as exc:
        results["invalid_config"] = {"passed": True, "error": type(exc).__name__}
    finally:
        os.environ.pop("NEXUS_SANDBOX__COMMAND_TIMEOUT_SECONDS", None)

    lock_conn = sqlite3.connect(config.database.path)
    lock_conn.execute("PRAGMA journal_mode=WAL")
    lock_conn.execute("BEGIN EXCLUSIVE")
    try:
        result = await orchestrator.run_task("list all python files")
        results["database_lock_during_task"] = {
            "passed": not result["success"],
            "error": result["error"],
            "message": result["message"],
        }
    finally:
        lock_conn.rollback()
        lock_conn.close()

    violation = await orchestrator.run_task("run command echo ok && dir")
    results["sandbox_violation"] = {
        "passed": not violation["success"],
        "error": violation["error"],
        "message": violation["message"],
    }

    original_append = orchestrator.event_store.append

    async def failing_append(event: Event) -> str:
        if event.event_type == "task_completed":
            raise RuntimeError("injected event write failure")
        return await original_append(event)

    orchestrator.event_store.append = failing_append  # type: ignore[assignment]
    partial = await orchestrator.run_task("create partial.txt with content partial")
    orchestrator.event_store.append = original_append  # type: ignore[assignment]
    results["orchestrator_crash_during_event_write"] = {
        "passed": partial.get("persistence_warning") is not None,
        "message": partial.get("persistence_warning"),
        "success": partial["success"],
    }

    identity = IdentityStore(config.database.path.parent)
    identity.write({"user": "gaurav"})
    identity.data_path.write_bytes(b"corrupted")
    try:
        identity.read()
        results["corrupted_identity_state"] = {
            "passed": False,
            "reason": "Expected decrypt failure.",
        }
    except InvalidToken as exc:
        results["corrupted_identity_state"] = {
            "passed": False,
            "error": type(exc).__name__,
            "message": "IdentityStore still crashes on corrupted ciphertext.",
        }

    original_complete = orchestrator.router.complete

    async def timeout_complete(intent_result, preferred):
        raise TimeoutError("injected provider timeout")

    orchestrator.router.complete = timeout_complete  # type: ignore[assignment]
    provider_timeout = await orchestrator.run_task("hello")
    orchestrator.router.complete = original_complete  # type: ignore[assignment]
    results["provider_timeout"] = {
        "passed": not provider_timeout["success"],
        "error": provider_timeout["error"],
        "message": provider_timeout["message"],
    }

    async def malformed_complete(intent_result, preferred):
        return {"bad": "shape"}

    orchestrator.router.complete = malformed_complete  # type: ignore[assignment]
    malformed = await orchestrator.run_task("hello")
    orchestrator.router.complete = original_complete  # type: ignore[assignment]
    results["malformed_provider_response"] = {
        "passed": not malformed["success"],
        "error": malformed["error"],
        "message": malformed["message"],
    }

    results["telemetry_snapshot"] = orchestrator.get_telemetry_snapshot()  # type: ignore[assignment]
    await orchestrator.close()
    return results


async def main() -> None:
    workspace = ROOT / ".failure-workspace"
    workspace.mkdir(exist_ok=True)
    (workspace / "src").mkdir(exist_ok=True)
    (workspace / "src" / "sample.py").write_text("print('x')\n", encoding="utf-8")
    results = await inject_failures(workspace)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
