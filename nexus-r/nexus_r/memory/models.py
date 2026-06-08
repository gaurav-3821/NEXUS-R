"""Pydantic models for the NEXUS-R Memory Management System."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    """Single source of truth for timestamps across the memory module."""
    return datetime.now(timezone.utc)


class UserFact(BaseModel):
    """A single extracted fact with metadata for importance, type, and origin."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    fact_text: str
    importance_score: float = Field(default=0.5, ge=0.0, le=1.0)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    type: Literal["semantic", "golden", "persistent", "smart"] = "semantic"
    source_conversation_id: str | None = None
    source_message_id: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    expires_at: datetime | None = None
    last_referenced_at: datetime | None = None

    def relevance_score(self, current_task: str | None = None) -> float:
        """Composite score used for ranking facts in the sliding window."""
        base = self.importance_score * self.confidence
        if current_task and self.fact_text:
            overlap = len(
                set(self.fact_text.lower().split())
                & set(current_task.lower().split())
            )
            task_bonus = min(overlap / 10.0, 0.3)
            base += task_bonus
        return min(base, 1.0)


class MemoryStats(BaseModel):
    """Statistics returned by the GET /memory/stats endpoint."""

    total_memories: int = 0
    total_size_bytes: int = 0
    categories: dict[str, int] = Field(
        default_factory=lambda: {
            "semantic": 0,
            "golden": 0,
            "persistent": 0,
            "smart": 0,
        }
    )
    oldest_memory_date: str | None = None
    newest_memory_date: str | None = None

    @classmethod
    def from_facts(cls, facts: list[UserFact]) -> MemoryStats:
        """Aggregate a list of UserFact objects into a MemoryStats snapshot."""
        total = len(facts)
        total_bytes = sum(len(f.fact_text.encode("utf-8")) for f in facts)
        cats: dict[str, int] = {
            "semantic": 0,
            "golden": 0,
            "persistent": 0,
            "smart": 0,
        }
        dates: list[datetime] = []
        for f in facts:
            cats[f.type] = cats.get(f.type, 0) + 1
            dates.append(f.created_at)
        return cls(
            total_memories=total,
            total_size_bytes=total_bytes,
            categories=cats,
            oldest_memory_date=min(dates).isoformat() if dates else None,
            newest_memory_date=max(dates).isoformat() if dates else None,
        )


class BlackboardState(BaseModel):
    """Rolling shared context that the Model Orchestrator passes to each AI."""

    conversation_id: str
    current_task: str = ""
    constraints: list[str] = Field(default_factory=list)
    progress: str = ""
    extracted_facts: list[UserFact] = Field(default_factory=list)
    compressed_summary: str = ""
    last_model_used: str = ""
    token_budget: int = 4096
    chat_ring: list[str] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=_utcnow)

    def trim_facts_to_budget(self, current_task: str | None = None) -> list[UserFact]:
        """Keep only the most relevant facts that fit within token_budget."""
        if not self.extracted_facts:
            return []

        scored = [(f, f.relevance_score(current_task)) for f in self.extracted_facts]
        scored.sort(key=lambda x: x[1], reverse=True)

        kept: list[UserFact] = []
        used_tokens = 0
        approx_tokens_per_char = 0.4

        for fact, _score in scored:
            cost = int(len(fact.fact_text) * approx_tokens_per_char)
            if used_tokens + cost > self.token_budget:
                break
            kept.append(fact)
            used_tokens += cost

        self.extracted_facts = kept
        return kept
