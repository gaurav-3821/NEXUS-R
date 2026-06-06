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
    raw_input: str = ""

@dataclass
class ResearchResult:
    sources: list[tuple[str, str, str]]  # (title, url, snippet)
    context: str
    context_for_prompt: str = ""
    widgets: list[dict] = field(default_factory=list)

class ResearchEngine:
    def __init__(self, search_registry):
        self.search_registry = search_registry

    async def run(self, intent, mode: str, sources: list[str] | None = None) -> ResearchResult:
        if mode == "speed" or not sources:
            return ResearchResult(sources=[], context="", context_for_prompt="")

        import asyncio
        try:
            results = await asyncio.wait_for(
                self.search_registry.search(
                    query=intent.raw_input,
                    categories=sources or ["web"],
                    limit=3 if mode == "balanced" else 10,
                ),
                timeout=10.0,
            )
        except asyncio.TimeoutError:
            logger.warning("Search timed out")
            return ResearchResult(sources=[], context="", context_for_prompt="")

        if not results.results:
            return ResearchResult(sources=[], context="", context_for_prompt="")

        src_list = [(r.title, r.url, r.content[:200]) for r in results.results[:5]]

        context_tasks = []
        valid_results = results.results[:2]
        
        for r in valid_results:
            if mode == "quality" and len(r.content) < 500:
                context_tasks.append(self._extract_with_timeout(r.url))
            else:
                context_tasks.append(self._return_snippet(r.content))

        extracted_contents = await asyncio.gather(*context_tasks, return_exceptions=True)
        
        context_parts = []
        for r, content in zip(valid_results, extracted_contents):
            if isinstance(content, Exception):
                logger.warning(f"Extraction failed for {r.url}: {content}")
                content = r.content
                
            safe_title = r.title.replace("<", "").replace(">", "")
            context_parts.append(f"<source title=\"{safe_title}\" url=\"{r.url}\">\n{content}\n</source>")

        context_str = "\n\n".join(context_parts)

        return ResearchResult(
            sources=src_list,
            context=context_str,
            context_for_prompt=context_str,
        )

    @staticmethod
    async def _return_snippet(text: str) -> str:
        return text

    async def _extract_with_timeout(self, url: str, timeout: float = 15.0) -> str:
        try:
            return await asyncio.wait_for(self.search_registry.extract(url), timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning(f"Extraction timed out for {url}")
            return ""
