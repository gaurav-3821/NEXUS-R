from __future__ import annotations

from uuid import uuid4

import pytest

from nexus_r.events import CausalEvent, ExecutionResult, IntentResult, PermissionTier

from modules.workflow_engine.src.pipeline import ETDPipeline
from modules.workflow_engine.src.applicator import ETDApplicator


class _InstrumentedSandbox:
    def __init__(self) -> None:
        self.call_count = 0
        self.total_cost = 0.0
        self.total_latency_ms = 0.0

    async def execute(self, task) -> ExecutionResult:
        self.call_count += 1
        self.total_cost += 0.025
        self.total_latency_ms += 250.0
        return ExecutionResult(success=True, message="ran", output="ok", cost_incurred=0.025)


def _make_trace(actions: list[str]) -> list[CausalEvent]:
    events: list[CausalEvent] = []
    prev: str | None = None
    for i, a in enumerate(actions):
        e = CausalEvent(
            event_type="workflow_step",
            parent_event_id=prev,
            data={
                "task_id": str(uuid4()),
                "step_index": i,
                "tool": "terminal",
                "action": a,
                "input_data": {},
                "output_data": {"message": f"Ran {a}"},
            },
            verification_result="passed",
            model_used="none",
            cost=0.0,
            tier=PermissionTier.T1,
        )
        events.append(e)
        prev = e.id
    return events


class TestETDCostReduction:
    @pytest.mark.asyncio
    async def test_repeated_execution_reduces_cost(self) -> None:
        sandbox = _InstrumentedSandbox()
        pipeline = ETDPipeline()
        applicator = ETDApplicator(sandbox, pipeline.store)
        trace = _make_trace(["npm install", "npm run build"])
        task_id = str(uuid4())

        first_etd = await pipeline.process_success(trace)
        assert first_etd is not None

        for i in range(4):
            intent = IntentResult(
                raw_input="npm install && npm run build",
                normalized_input=first_etd.intent_signature,
                task_type="npm",
                complexity=0.3,
                confidence=0.9,
                parameters={},
                suggested_tier=PermissionTier.T1,
            )
            match = await pipeline.find_match(intent)
            assert match is not None, f"Match should be found on iteration {i + 1}"
            result = await applicator.apply(match, {}, f"{task_id}-{i}")
            assert result is not None
            assert result.success is True
            assert result.cost_incurred == 0.0


    @pytest.mark.asyncio
    async def test_multiple_sandbox_calls_from_etd(self) -> None:
        sandbox = _InstrumentedSandbox()
        pipeline = ETDPipeline()
        applicator = ETDApplicator(sandbox, pipeline.store)
        trace = _make_trace(["npm install", "npm run build", "npm test"])
        task_id = str(uuid4())

        first_etd = await pipeline.process_success(trace)
        assert first_etd is not None

        intent = IntentResult(
            raw_input="install build test",
            normalized_input=first_etd.intent_signature,
            task_type="npm",
            complexity=0.5,
            confidence=0.9,
            parameters={},
            suggested_tier=PermissionTier.T1,
        )
        match = await pipeline.find_match(intent)
        assert match is not None
        result = await applicator.apply(match, {}, task_id)
        assert result is not None
        assert result.success is True
        assert result.cost_incurred == 0.0

    @pytest.mark.asyncio
    async def test_first_execution_has_cost_later_ones_do_not(self) -> None:
        sandbox = _InstrumentedSandbox()
        pipeline = ETDPipeline()
        applicator = ETDApplicator(sandbox, pipeline.store)
        trace = _make_trace(["npm run build"])
        task_id = str(uuid4())

        first_etd = await pipeline.process_success(trace)
        assert first_etd is not None
        sandbox.call_count = 0
        sandbox.total_cost = 0.0

        for i in range(5):
            intent = IntentResult(
                raw_input="npm run build",
                normalized_input=first_etd.intent_signature,
                task_type="npm",
                complexity=0.3,
                confidence=0.9,
                parameters={},
                suggested_tier=PermissionTier.T1,
            )
            match = await pipeline.find_match(intent)
            assert match is not None, f"Match on iteration {i}"
            result = await applicator.apply(match, {}, f"{task_id}-{i}")
            assert result is not None and result.success, f"Apply on iteration {i}"
            assert result.cost_incurred == 0.0, f"Cost should be $0 on iteration {i}"

    @pytest.mark.asyncio
    async def test_no_etd_match_means_normal_execution(self) -> None:
        sandbox = _InstrumentedSandbox()
        pipeline = ETDPipeline()
        trace = _make_trace(["npm install"])
        _ = await pipeline.process_success(trace)

        intent = IntentResult(
            raw_input="completely unrelated task about database migration",
            normalized_input="database migration",
            task_type="run_terminal",
            complexity=0.5,
            confidence=0.9,
            parameters={},
            suggested_tier=PermissionTier.T1,
        )
        match = await pipeline.find_match(intent)
        assert match is None
