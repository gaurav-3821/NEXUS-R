from __future__ import annotations

from uuid import uuid4

import pytest

from nexus_r.config import NEXUSConfig
from nexus_r.events import CausalEvent, IntentResult, PermissionTier

from modules.orchestrator.src.orchestrator import MainOrchestrator
from modules.workflow_engine.src.pipeline import ETDPipeline


class TestOrchestratorETDIntegration:
    @pytest.mark.asyncio
    async def test_router_returns_etd_match_false(self, workspace) -> None:
        config = NEXUSConfig.default(workspace)
        orchestrator = MainOrchestrator(config)
        await orchestrator.initialize()
        try:
            result = await orchestrator.run_task("list all python files")
            assert result["success"] is True

            routing_events = await orchestrator.event_store.get_by_type("routing_decided")
            assert len(routing_events) >= 1
            latest = routing_events[-1]
            assert latest.data.get("etd_match_found") is False
        finally:
            await orchestrator.event_store.close()

    @pytest.mark.asyncio
    async def test_orchestrator_queries_etd_store_independently(self, workspace) -> None:
        config = NEXUSConfig.default(workspace)
        orchestrator = MainOrchestrator(config)
        await orchestrator.initialize()
        try:
            task_input = "list all python files"
            result1 = await orchestrator.run_task(task_input)
            assert result1["success"] is True

            first_routing = await orchestrator.event_store.get_by_type("routing_decided")
            assert len(first_routing) >= 1

            result2 = await orchestrator.run_task(task_input)
            assert result2["success"] is True

            second_routing = await orchestrator.event_store.get_by_type("routing_decided")
            etd_cached_event = await orchestrator.event_store.get_by_type("workflow_step")

            etd_from_cache = any(
                e.data.get("tool") == "etd_cache" for e in etd_cached_event
            )
            if etd_from_cache:
                assert len(second_routing) == len(first_routing), (
                    "No new routing_decided events expected when ETD cache is hit"
                )
        finally:
            await orchestrator.event_store.close()

    @pytest.mark.asyncio
    async def test_etd_cache_hit_skips_router(self) -> None:
        pipeline = ETDPipeline()
        from modules.workflow_engine.src.parameterizer import WorkflowParameterizer
        from modules.workflow_engine.src.distiller import DistilledWorkflow, ToolStep

        intent_signature = "run-terminal-npm-install"
        intent = IntentResult(
            raw_input="npm install",
            normalized_input=intent_signature,
            task_type="run_terminal",
            complexity=0.3,
            confidence=0.9,
            parameters={},
            suggested_tier=PermissionTier.T1,
        )

        match_before = await pipeline.find_match(intent)
        assert match_before is None

        wf = DistilledWorkflow(
            id=str(uuid4()),
            intent_signature=intent_signature,
            tool_sequence=[ToolStep(tool="terminal", action="npm install", verify="passed")],
            parameter_slots=[],
            invariant_checks=[],
            success_count=1,
            failure_count=0,
            generalization_success_rate=1.0,
        )
        entry = WorkflowParameterizer().parameterize(wf)
        entry.generalization_success_rate = 1.0
        pipeline.indexer.index(entry)

        match_after = await pipeline.find_match(intent)
        assert match_after is not None
        assert match_after.id == entry.id
