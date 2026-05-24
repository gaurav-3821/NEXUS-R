from __future__ import annotations

from typing import Any, Sequence

from nexus_r.events import CausalEvent, IntentResult

from modules.workflow_engine.src.distiller import TraceDistiller, DistilledWorkflow
from modules.workflow_engine.src.generalizer import (
    GeneralizationVerifier,
    GeneralizationResult,
    TaskVariant,
    TOOL_ENV_MAP,
)
from modules.workflow_engine.src.parameterizer import ETDEntry, WorkflowParameterizer
from modules.workflow_engine.src.indexer import ETDIndexer
from modules.workflow_engine.src.retriever import ETDRetriever, RetrievalQuery, compute_embedding
from modules.workflow_engine.src.invalidator import ETDInvalidator
from modules.workflow_engine.src.store import ETDStore


MIN_MATCH_SCORE = 0.85
MIN_GENERALIZATION_RATE = 0.90
NUM_VARIANTS = 10


class ETDPipeline:
    def __init__(self) -> None:
        self.store = ETDStore()
        self.distiller = TraceDistiller()
        self.generalizer = GeneralizationVerifier()
        self.parameterizer = WorkflowParameterizer()
        self.indexer = ETDIndexer(self.store)
        self.retriever = ETDRetriever(self.store)
        self.invalidator = ETDInvalidator(self.store)

    async def process_success(self, trace: Sequence[CausalEvent], normalized_input: str = "", cost: float = 0.0, latency_ms: float = 0.0) -> ETDEntry | None:
        workflow = self.distiller.distill(trace)
        if not workflow.tool_sequence:
            return None
        variants = self._auto_variants(workflow)
        result = self.generalizer.verify(workflow, variants)
        if not result.admitted:
            return None
        entry = self.parameterizer.parameterize(workflow, cost=cost, latency_ms=latency_ms)
        entry.generalization_success_rate = result.success_rate
        if normalized_input:
            entry.intent_embedding = compute_embedding(normalized_input)
        self.indexer.index(entry)
        return entry

    async def find_match(self, intent: IntentResult) -> ETDEntry | None:
        query = RetrievalQuery(
            normalized_input=intent.normalized_input,
            action_type=intent.task_type,
            parameters=dict(intent.parameters),
            max_results=1,
            min_score=MIN_MATCH_SCORE,
        )
        results = self.retriever.retrieve(query)
        for ranked in results:
            entry = ranked.entry
            if entry.entry.generalization_success_rate >= MIN_GENERALIZATION_RATE:
                return entry.entry
        return None

    async def invalidate_stale(self) -> list[str]:
        rules = self.invalidator.run_all()
        ids: list[str] = []
        for rule in rules:
            ids.extend(rule.entry_ids)
        return ids

    def _auto_variants(self, workflow: DistilledWorkflow) -> list[TaskVariant]:
        cmd_env_map = {
            "npm": "node_version", "node": "node_version",
            "pip": "python_version", "python": "python_version",
            "vercel": "vercel_version", "git": "git_version",
            "docker": "docker_version", "java": "java_version",
        }
        needed: set[str] = set()
        for step in workflow.tool_sequence:
            cmd = step.action.split()[0].lower() if step.action.strip() else ""
            if cmd in cmd_env_map:
                needed.add(cmd_env_map[cmd])
        for inv in workflow.invariant_checks:
            tool = inv.split()[0].lower()
            env_key = TOOL_ENV_MAP.get(tool, f"{tool}_version")
            needed.add(env_key)
        variants: list[TaskVariant] = []
        for i in range(NUM_VARIANTS):
            params: dict[str, str] = {}
            env: dict[str, str] = {}
            for slot in workflow.parameter_slots:
                params[slot] = f"variant-{i}-val"
            for env_key in sorted(needed):
                env[env_key] = f"{18 + i}.0"
            variants.append(TaskVariant(
                name=f"v{i}",
                parameters=params,
                environment=env,
                expected_success=True,
            ))
        return variants
