from __future__ import annotations

import json
from time import monotonic

import pytest
from typer.testing import CliRunner

from modules.cli.src.main import app
from modules.orchestrator.src.orchestrator import MainOrchestrator
from nexus_r.config import NEXUSConfig


COLD_START_THRESHOLD_S = 15.0


@pytest.mark.asyncio
async def test_orchestrator_full_pipeline_and_causal_chain(workspace) -> None:
    config = NEXUSConfig.default(workspace)
    orchestrator = MainOrchestrator(config)
    started = monotonic()
    list_result = await orchestrator.run_task("list all python files")
    create_result = await orchestrator.run_task("create test.txt")
    elapsed = monotonic() - started

    assert list_result["success"] is True
    assert create_result["success"] is True
    assert (workspace / "test.txt").exists()
    assert elapsed < COLD_START_THRESHOLD_S, (
        f"Cold-start pipeline took {elapsed:.2f}s (threshold {COLD_START_THRESHOLD_S}s). "
        "This is a cold-start performance benchmark, not a functional assertion. "
        "Known limitation: first invocations load model registry, create DB schemas, and "
        "warm up provider connections. On Windows, observed cold-start ~5.9s for 2 tasks."
    )

    history = await orchestrator.get_history()
    costs = await orchestrator.get_cost_summary()
    assert len(history) == 2
    assert "totals" in costs

    completed_events = await orchestrator.event_store.get_by_type("task_completed")
    final_event = completed_events[-1]
    chain = await orchestrator.event_store.get_chain(final_event.id)
    event_types = [event.event_type for event in chain]
    assert event_types[:3] == ["task_received", "intent_parsed", "audit_log"]
    assert "workflow_step" in event_types
    assert event_types[-1] == "task_completed"
    session_id = orchestrator.session_id
    await orchestrator.event_store.close()
    assert session_id is not None

    resumed = MainOrchestrator(config)
    await resumed.initialize()
    assert resumed.session_id == session_id
    snapshot = resumed.session_manager.resume_session(session_id, workspace)
    assert snapshot.sequence >= 4
    assert snapshot.state["working_state"]["latest_task_id"] == create_result["task_id"]
    await resumed.close()


def test_cli_commands(workspace) -> None:
    runner = CliRunner()
    result_run = runner.invoke(app, ["run", "list all python files", "--workspace", str(workspace)])
    assert result_run.exit_code == 0
    payload = json.loads(result_run.stdout)
    assert payload["success"] is True

    result_history = runner.invoke(app, ["history", "--workspace", str(workspace)])
    assert result_history.exit_code == 0
    history = json.loads(result_history.stdout)
    assert history

    result_cost = runner.invoke(app, ["cost", "--workspace", str(workspace)])
    assert result_cost.exit_code == 0
    costs = json.loads(result_cost.stdout)
    assert "totals" in costs
