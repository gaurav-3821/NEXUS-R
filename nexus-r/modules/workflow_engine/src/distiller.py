from __future__ import annotations

from dataclasses import dataclass, field
from re import Pattern
import re
from typing import Sequence
from uuid import uuid4

from nexus_r.events import CausalEvent


@dataclass
class ToolStep:
    tool: str
    action: str
    verify: str
    is_essential: bool = True


@dataclass
class DistilledWorkflow:
    id: str
    intent_signature: str
    tool_sequence: list[ToolStep]
    parameter_slots: list[str]
    invariant_checks: list[str]
    success_count: int
    failure_count: int
    generalization_success_rate: float = 0.0


EXPLORATORY_PATTERNS: list[Pattern] = [
    re.compile(r"^(ls|dir|ll)\b"),
    re.compile(r"^(cat|type|echo|pwd|which|where)\b"),
    re.compile(r"^(find|locate|grep|search)\b"),
    re.compile(r"--version$"),
    re.compile(r"^-{1,2}v\b"),
]

VERSION_CHECK_PATTERNS: list[Pattern] = [
    re.compile(r"(node|npm|vercel|python|git|docker|java)\s--version"),
    re.compile(r"(node|npm|vercel|python|git|docker|java)\s-v\b"),
]

PATH_PATTERN: Pattern = re.compile(
    r"(?:/[\w.-]+)+|(?:[A-Za-z]:\\[ \w.\-\\]+)"
)


class TraceDistiller:
    def distill(self, trace: Sequence[CausalEvent]) -> DistilledWorkflow:
        if not trace:
            return self._empty()
        event_map = {e.id: e for e in trace}
        children = self._build_children_map(trace)
        main_leaf = self._find_main_leaf(trace, children)
        essential_path = self._walk_chain(main_leaf, event_map)
        cleaned = self._collapse_retries(essential_path)
        cleaned = self._remove_exploratory(cleaned)
        cleaned = self._dedup_verification(cleaned)
        invariants = self._extract_invariants_from_trace(trace)
        tool_steps = [self._to_tool_step(e) for e in cleaned]
        slots = self._identify_parameter_slots(cleaned)
        sig = self._derive_intent_signature(cleaned)
        return DistilledWorkflow(
            id=str(uuid4()),
            intent_signature=sig,
            tool_sequence=tool_steps,
            parameter_slots=slots,
            invariant_checks=invariants,
            success_count=1,
            failure_count=0,
            generalization_success_rate=0.0,
        )

    def _build_children_map(self, trace: Sequence[CausalEvent]) -> dict[str, list[CausalEvent]]:
        children: dict[str, list[CausalEvent]] = {}
        for e in trace:
            pid = e.parent_event_id
            if pid is not None:
                children.setdefault(pid, []).append(e)
        return children

    def _find_root(self, trace: Sequence[CausalEvent], event_map: dict[str, CausalEvent]) -> CausalEvent | None:
        for e in trace:
            if e.parent_event_id is None or e.parent_event_id not in event_map:
                return e
        return trace[0] if trace else None

    def _find_main_leaf(self, trace: Sequence[CausalEvent], children: dict[str, list[CausalEvent]]) -> CausalEvent:
        leaves = [e for e in trace if e.id not in children]
        if not leaves:
            return trace[-1]
        leaves.sort(key=lambda e: e.data.get("step_index", 0), reverse=True)
        return leaves[0]

    def _walk_chain(self, leaf: CausalEvent, event_map: dict[str, CausalEvent]) -> list[CausalEvent]:
        chain: list[CausalEvent] = []
        current: CausalEvent | None = leaf
        while current is not None:
            chain.append(current)
            pid = current.parent_event_id
            current = event_map.get(pid) if pid is not None else None
        chain.reverse()
        return chain

    def _collapse_retries(self, chain: list[CausalEvent]) -> list[CausalEvent]:
        if not chain:
            return []
        result: list[CausalEvent] = [chain[0]]
        for e in chain[1:]:
            prev = result[-1]
            e_tool = e.data.get("tool", "")
            e_action = e.data.get("action", "")
            p_tool = prev.data.get("tool", "")
            p_action = prev.data.get("action", "")
            if e_tool == p_tool and e_action == p_action:
                result[-1] = e
            else:
                result.append(e)
        return result

    def _is_exploratory(self, event: CausalEvent) -> bool:
        action: str = event.data.get("action", "")
        action_lower = action.strip().lower()
        for pat in EXPLORATORY_PATTERNS:
            if pat.search(action_lower):
                return True
        return False

    def _remove_exploratory(self, chain: list[CausalEvent]) -> list[CausalEvent]:
        return [e for e in chain if not self._is_exploratory(e)]

    def _is_verification_event(self, event: CausalEvent) -> bool:
        action: str = event.data.get("action", "")
        tool: str = event.data.get("tool", "")
        return tool == "terminal" and action.startswith("curl")

    def _dedup_verification(self, chain: list[CausalEvent]) -> list[CausalEvent]:
        if not chain:
            return []
        result: list[CausalEvent] = [chain[0]]
        for e in chain[1:]:
            prev = result[-1]
            e_tool = e.data.get("tool", "")
            p_tool = prev.data.get("tool", "")
            is_verif = self._is_verification_event(e)
            was_verif = self._is_verification_event(prev)
            if is_verif and was_verif and e_tool == p_tool:
                result[-1] = e
            else:
                result.append(e)
        return result

    def _extract_invariants_from_trace(self, trace: Sequence[CausalEvent]) -> list[str]:
        invariants: list[str] = []
        seen: set[str] = set()
        for e in trace:
            action: str = e.data.get("action", "")
            action_lower = action.strip().lower()
            for pat in VERSION_CHECK_PATTERNS:
                m = pat.search(action_lower)
                if m:
                    tool_name = m.group(1).capitalize()
                    invariant = f"{tool_name} available"
                    if invariant not in seen:
                        invariants.append(invariant)
                        seen.add(invariant)
        return invariants

    def _to_tool_step(self, event: CausalEvent) -> ToolStep:
        return ToolStep(
            tool=str(event.data.get("tool", "unknown")),
            action=str(event.data.get("action", "")),
            verify=event.verification_result,
            is_essential=True,
        )

    def _identify_parameter_slots(self, chain: list[CausalEvent]) -> list[str]:
        slots: list[str] = []
        seen_slots: set[str] = set()
        common_dirs = {"home", "Users", "Documents", "Desktop", "tmp", "var",
                       "etc", "opt", "usr", "bin", "lib", "root", "app", "src",
                       "dev", "proc", "sys", "mnt", "media", "sbin", "run",
                       "data", "config", "cache", "local", "share"}
        for e in chain:
            action: str = e.data.get("action", "")
            matches = PATH_PATTERN.findall(action)
            for path in matches:
                parts = path.replace("\\", "/").strip("/").split("/")
                tail = None
                for seg in reversed(parts):
                    if seg not in common_dirs and not seg.startswith("."):
                        tail = seg
                        break
                if tail is None:
                    continue
                if re.match(r"^[a-z]+[-_][a-z0-9]+$", tail, re.IGNORECASE) or \
                   re.match(r"^[a-z]+-\d+$", tail, re.IGNORECASE):
                    slot = "project_dir"
                else:
                    slot = f"{tail.lower()}_dir"
                if slot not in seen_slots:
                    slots.append(slot)
                    seen_slots.add(slot)
        return slots

    def _derive_intent_signature(self, chain: list[CausalEvent]) -> str:
        actions = []
        for e in chain:
            action: str = e.data.get("action", "")
            action = action.split("/")[0].strip()
            action = re.sub(r"[^a-zA-Z0-9]", "_", action)
            action = re.sub(r"_+", "_", action).strip("_")
            if action:
                actions.append(action.lower())
        return "-".join(actions) if actions else "empty"

    def _empty(self) -> DistilledWorkflow:
        return DistilledWorkflow(
            id=str(uuid4()),
            intent_signature="empty",
            tool_sequence=[],
            parameter_slots=[],
            invariant_checks=[],
            success_count=0,
            failure_count=0,
            generalization_success_rate=0.0,
        )
