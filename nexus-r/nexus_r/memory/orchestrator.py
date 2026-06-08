"""ModelOrchestrator — compresses BlackboardState into a model prompt and delegates to ModelRegistry."""

from __future__ import annotations

from datetime import datetime, timezone

from nexus_r.memory.manager import MemoryManager
from nexus_r.memory.models import BlackboardState
from nexus_r.model_registry import ModelRegistry


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ModelOrchestrator:
    """Takes BlackboardState → builds enriched prompt → calls ModelRegistry → returns updated state.

    This is the bridge between the memory subsystem (MemoryManager, BlackboardState)
    and the model selection subsystem (ModelRegistry). It does NOT contain its own
    routing logic — it delegates model selection to ModelRegistry which uses the
    existing heuristic + semantic + CAR tier pipeline.
    """

    def __init__(self, memory_manager: MemoryManager, model_registry: ModelRegistry) -> None:
        self.memory_manager = memory_manager
        self.models = model_registry
        self._ring_max = 6  # 3 user + 3 assistant turns

    async def execute_turn(self, user_input: str, state: BlackboardState, preferred: str = "auto") -> BlackboardState:
        """Process one conversational turn: update state, build prompt, call model, return updated state."""
        # 1. Append user turn to ring buffer
        state.chat_ring.append(f"User: {user_input}")
        state.chat_ring = state.chat_ring[-self._ring_max:]

        # 2. Assemble prompt from current state
        prompt = await self._build_prompt(state, user_input)

        # 3. Call ModelRegistry (reuses existing heuristic+semantic+provider-chain routing)
        result = await self.models.complete(prompt=prompt, preferred=preferred)

        # 4. Update state with response
        state.last_model_used = result.model_name
        state.chat_ring.append(f"Assistant: {result.text}")
        state.chat_ring = state.chat_ring[-self._ring_max:]
        snippet = result.text[:200].replace("\n", " ")
        state.progress = f"Assistant: {snippet}..."
        state.updated_at = _utcnow()

        # 5. Auto-extract fresh facts every 3 full turns
        turns = len(state.chat_ring) // 2
        if turns > 0 and turns % 3 == 0 and self.memory_manager is not None:
            try:
                await self.memory_manager.auto_extract_and_compress(
                    raw_chat_history=state.chat_ring,
                    conversation_id=state.conversation_id,
                )
            except Exception:
                pass

        return state

    async def execute_turn_stream(self, user_input: str, state: BlackboardState, preferred: str = "auto"):
        """Like execute_turn but yields ModelStreamChunk tokens as they arrive.

        After iteration completes the state is automatically updated (chat_ring,
        progress, last_model_used, auto-extraction every 3 turns).
        """
        state.chat_ring.append(f"User: {user_input}")
        state.chat_ring = state.chat_ring[-self._ring_max:]

        prompt = await self._build_prompt(state, user_input)
        full_text = ""
        last_model = ""

        async for chunk in self.models.stream(prompt=prompt, preferred=preferred):
            full_text += chunk.text
            last_model = chunk.model_name
            yield chunk

        state.last_model_used = last_model
        state.chat_ring.append(f"Assistant: {full_text}")
        state.chat_ring = state.chat_ring[-self._ring_max:]
        snippet = full_text[:200].replace("\n", " ")
        state.progress = f"Assistant: {snippet}..."
        state.updated_at = _utcnow()

        turns = len(state.chat_ring) // 2
        if turns > 0 and turns % 3 == 0 and self.memory_manager is not None:
            try:
                await self.memory_manager.auto_extract_and_compress(
                    raw_chat_history=state.chat_ring,
                    conversation_id=state.conversation_id,
                )
            except Exception:
                pass

    async def _build_prompt(self, state: BlackboardState, user_input: str = "") -> str:
        """Compress BlackboardState into a context prompt with semantic fact retrieval."""
        parts = []

        parts.append("[BLACKBOARD STATE HANDOFF]")
        parts.append(f"Conversation: {state.conversation_id}")
        parts.append(f"Current task: {state.current_task}")
        if state.constraints:
            parts.append(f"Constraints: {'; '.join(state.constraints)}")
        parts.append(f"Progress so far: {state.progress or 'Not started yet.'}")

        if state.compressed_summary:
            parts.append(f"\n[CONTEXT SUMMARY]\n{state.compressed_summary}")

        # Semantic search for relevant facts using the user's latest input
        query = user_input or (state.chat_ring[-1] if state.chat_ring else "")
        top_facts: list[UserFact] = []
        if self.memory_manager is not None and query:
            try:
                top_facts = await self.memory_manager.search_memories(query, limit=3)
            except Exception:
                pass

        if not top_facts and state.extracted_facts:
            sorted_facts = sorted(
                state.extracted_facts,
                key=lambda f: f.relevance_score(state.current_task),
                reverse=True,
            )
            top_facts = sorted_facts[:3]

        if top_facts:
            parts.append("\n[RELEVANT FACTS]")
            for f in top_facts:
                parts.append(f"  - {f.fact_text}  (confidence: {f.confidence})")

        if state.chat_ring:
            tail = state.chat_ring[-3:] if len(state.chat_ring) > 3 else state.chat_ring
            parts.append("\n[RECENT TURNS]")
            parts.extend(tail)

        parts.append(
            "\n[SYSTEM: MODEL HANDOFF]\n"
            f"You ({state.last_model_used or 'the primary model'}) are continuing this conversation. "
            "Respond naturally to the user's latest input using the context above."
        )

        return "\n\n".join(parts)
