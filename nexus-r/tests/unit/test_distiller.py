from __future__ import annotations

from uuid import uuid4

import pytest

from nexus_r.events import CausalEvent, PermissionTier
from modules.workflow_engine.src.distiller import TraceDistiller, ToolStep


def _make_event(
    tool: str,
    action: str,
    verify: str = "passed",
    parent_event_id: str | None = None,
    step_index: int = 0,
) -> CausalEvent:
    return CausalEvent(
        event_type="workflow_step",
        parent_event_id=parent_event_id,
        data={
            "tool": tool,
            "action": action,
            "input_data": {},
            "output_data": {"message": f"Ran {action}"},
            "task_id": str(uuid4()),
            "step_index": step_index,
        },
        verification_result=verify,
        model_used="none",
        cost=0.0,
        tier=PermissionTier.T1,
    )


def _make_chain(actions: list[tuple[str, str, str]]) -> list[CausalEvent]:
    events: list[CausalEvent] = []
    prev_id: str | None = None
    for idx, (tool, action, verify) in enumerate(actions):
        e = _make_event(tool, action, verify, parent_event_id=prev_id, step_index=idx)
        events.append(e)
        prev_id = e.id
    return events


def _actions_from(result: list[ToolStep]) -> list[str]:
    return [s.action for s in result]


class TestTraceDistiller:
    def test_simple_trace_removes_dead_end(self) -> None:
        actions = [
            ("terminal", "ls files", "passed"),
            ("terminal", "cat readme", "passed"),
            ("terminal", "npm run build", "passed"),
            ("terminal", "vercel deploy", "passed"),
        ]
        trace = _make_chain(actions)
        d = TraceDistiller().distill(trace)
        got = _actions_from(d.tool_sequence)
        assert got == ["npm run build", "vercel deploy"], f"got {got}"

    def test_retry_collapses_to_last_success(self) -> None:
        actions = [
            ("terminal", "npm install", "failed"),
            ("terminal", "npm install", "passed"),
            ("terminal", "npm run build", "passed"),
        ]
        trace = _make_chain(actions)
        d = TraceDistiller().distill(trace)
        got = _actions_from(d.tool_sequence)
        assert got == ["npm install", "npm run build"], f"got {got}"
        install_steps = [s for s in d.tool_sequence if s.action == "npm install"]
        assert len(install_steps) == 1
        assert install_steps[0].verify == "passed"

    def test_exploratory_version_check_removed(self) -> None:
        actions = [
            ("terminal", "vercel --version", "passed"),
            ("terminal", "npm run build", "passed"),
            ("terminal", "vercel deploy", "passed"),
        ]
        trace = _make_chain(actions)
        d = TraceDistiller().distill(trace)
        got = _actions_from(d.tool_sequence)
        assert got == ["npm run build", "vercel deploy"], f"got {got}"

    def test_full_causal_chain_preserved(self) -> None:
        actions = [
            ("terminal", "npm install", "passed"),
            ("terminal", "npm run build", "passed"),
            ("terminal", "vercel deploy", "passed"),
            ("terminal", "curl https://deploy-abc.vercel.app", "passed"),
        ]
        trace = _make_chain(actions)
        d = TraceDistiller().distill(trace)
        got = _actions_from(d.tool_sequence)
        assert got == [
            "npm install",
            "npm run build",
            "vercel deploy",
            "curl https://deploy-abc.vercel.app",
        ], f"got {got}"

    def test_parameter_slots_identified(self) -> None:
        actions = [
            ("terminal", "cd /home/user/project-a", "passed"),
            ("terminal", "npm run build", "passed"),
            ("terminal", "vercel deploy", "passed"),
        ]
        trace = _make_chain(actions)
        d = TraceDistiller().distill(trace)
        assert "project_dir" in d.parameter_slots, f"got slots {d.parameter_slots}"
        got = _actions_from(d.tool_sequence)
        assert "npm run build" in got
        assert "vercel deploy" in got

    def test_empty_trace_returns_empty_workflow(self) -> None:
        d = TraceDistiller().distill([])
        assert d.tool_sequence == []
        assert d.parameter_slots == []
        assert d.success_count == 0
        assert d.failure_count == 0

    def test_single_event_preserved(self) -> None:
        e = _make_event("terminal", "npm run build", "passed")
        d = TraceDistiller().distill([e])
        got = _actions_from(d.tool_sequence)
        assert got == ["npm run build"]

    def test_exploratory_ls_removed_from_front(self) -> None:
        actions = [
            ("terminal", "ls", "passed"),
            ("terminal", "npm run build", "passed"),
            ("terminal", "vercel deploy", "passed"),
        ]
        trace = _make_chain(actions)
        d = TraceDistiller().distill(trace)
        got = _actions_from(d.tool_sequence)
        assert got == ["npm run build", "vercel deploy"], f"got {got}"

    def test_verification_dedup_same_tool(self) -> None:
        actions = [
            ("terminal", "npm run build", "passed"),
            ("terminal", "curl http://test.com/health", "passed"),
            ("terminal", "curl http://test.com/ready", "passed"),
        ]
        trace = _make_chain(actions)
        d = TraceDistiller().distill(trace)
        got = _actions_from(d.tool_sequence)
        assert got == ["npm run build", "curl http://test.com/ready"], f"got {got}"

    def test_invariant_checks_extracted(self) -> None:
        actions = [
            ("terminal", "node --version", "passed"),
            ("terminal", "npm install", "passed"),
            ("terminal", "vercel --version", "passed"),
            ("terminal", "npm run build", "passed"),
            ("terminal", "vercel deploy", "passed"),
        ]
        trace = _make_chain(actions)
        d = TraceDistiller().distill(trace)
        assert "Node available" in d.invariant_checks, f"got {d.invariant_checks}"
        assert "Vercel available" in d.invariant_checks, f"got {d.invariant_checks}"
        got = _actions_from(d.tool_sequence)
        assert "npm install" in got
        assert "npm run build" in got
        assert "vercel deploy" in got
        assert "node --version" not in got
        assert "vercel --version" not in got
