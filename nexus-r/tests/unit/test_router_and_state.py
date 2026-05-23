from __future__ import annotations

import pytest

from nexus_r.config import NEXUSConfig
from nexus_r.events import Event, IntentResult, PermissionTier
from modules.cognition_router.src.router import CognitionRouter
from modules.state_core.src.identity_store import IdentityStore
from modules.state_core.src.event_store import EventStore
from modules.trust_layer.src.secret_registry import SecretRegistry


@pytest.mark.asyncio
async def test_router_marks_prior_success_and_escalates_byok(workspace, monkeypatch) -> None:
    monkeypatch.setenv("NEXUS_BYOK_API_KEY", "dummy")
    config = NEXUSConfig.default(workspace)
    store = EventStore(config.database.path)
    await store.initialize()
    secrets = SecretRegistry(config.app_name)
    secrets.bootstrap_from_environment(config.models.byok_secret_name, config.models.byok_api_key_env)
    await store.append(
        Event(
            event_type="task_completed",
            data={"normalized_input": "complex task", "success": True},
        )
    )
    router = CognitionRouter(config, store, secrets)
    intent = IntentResult(
        raw_input="complex task",
        normalized_input="complex task",
        task_type="run_terminal",
        complexity=0.9,
        confidence=0.9,
        parameters={"command": "echo hi"},
        suggested_tier=PermissionTier.T2,
    )
    decision = await router.route(intent)
    assert decision.etd_match_found is True
    assert decision.selected_model == config.models.byok_model
    await store.close()


def test_identity_store_encrypts_payload(workspace) -> None:
    store = IdentityStore(workspace / ".nexus-r")
    store.write({"user": "gaurav", "policy": "always_local"})
    raw_bytes = (workspace / ".nexus-r" / "identity.enc").read_bytes()
    assert b"gaurav" not in raw_bytes
    assert store.read()["policy"] == "always_local"
