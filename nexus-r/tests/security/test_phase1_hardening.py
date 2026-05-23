from __future__ import annotations

import pytest

from nexus_r.config import NEXUSConfig
from nexus_r.events import Action, PermissionTier
from modules.orchestrator.src.orchestrator import MainOrchestrator
from modules.trust_layer.src.permission_enforcer import PermissionEnforcer


def test_permission_enforcer_denies_unimplemented_tiers_and_redacts() -> None:
    enforcer = PermissionEnforcer()
    decision = enforcer.check(
        Action(
            name="delete_file",
            tier=PermissionTier.T4,
            metadata={"api_key": "secret", "path": "x.txt"},
        ),
        PermissionTier.T4,
    )
    assert decision.allowed is False
    assert decision.redacted_metadata["api_key"] == "***REDACTED***"


@pytest.mark.asyncio
async def test_unknown_task_is_rejected_without_execution(workspace) -> None:
    config = NEXUSConfig.default(workspace)
    orchestrator = MainOrchestrator(config)
    result = await orchestrator.run_task("deploy this to production and rotate all secrets")
    assert result["success"] is False
    assert result["message"] == "Unsupported Phase 1 task."

    sandbox_events = await orchestrator.event_store.get_by_type("sandbox_invocation")
    assert sandbox_events == []
    await orchestrator.event_store.close()
