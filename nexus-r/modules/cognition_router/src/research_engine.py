from __future__ import annotations
from dataclasses import dataclass, field
import logging
from .providers.search_provider import SearchResponse

logger = logging.getLogger("nexus-r.research")

@dataclass
class PipelineContext:
    """Context object passed to widgets and downstream processes."""
    research_result: 'ResearchResult | None' = None
    memory_facts: list[dict] = field(default_factory=list)
    router_decision: dict = field(default_factory=dict)

@dataclass
class ResearchResult:
    sources: list[tuple[str, str, str]]  # (title, url, snippet)
    context: str
    context_for_prompt: str = ""
    widgets: list[dict] = field(default_factory=list)

class ResearchEngine:
    def __init__(self, search_registry, widget_registry=None):
        self.search_registry = search_registry
        self.widget_registry = widget_registry

    async def run(self, intent, mode: str, sources: list[str] | None = None) -> ResearchResult:
        if mode == "speed" or not sources:
            return ResearchResult(sources=[], context="", context_for_prompt="")

        results = await self.search_registry.search(
            query=intent.raw_input,
            categories=sources or ["web"],
            limit=3 if mode == "balanced" else 10,
        )

        if not results.results:
            return ResearchResult(sources=[], context="", context_for_prompt="")

        src_list = [(r.title, r.url, r.content[:200]) for r in results.results[:5]]

        context_parts = []
        for r in results.results[:2]:
            content = r.content
            if mode == "quality" and len(content) < 500:
                extracted = await self.search_registry.extract(r.url)
                if extracted:
                    content = extracted
            context_parts.append(f"--- Source: {r.title} ({r.url}) ---\n{content}")

        context_str = "\n\n".join(context_parts)

        return ResearchResult(
            sources=src_list,
            context=context_str,
            context_for_prompt=context_str,
        )
