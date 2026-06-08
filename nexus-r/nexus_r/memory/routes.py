"""FastAPI router for the /memory endpoints expected by the frontend."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from nexus_r.memory.manager import MemoryManager, get_toggles, set_toggle
from nexus_r.memory.models import UserFact

router = APIRouter(prefix="/api/v1/memory", tags=["memory"])

_manager: MemoryManager | None = None


def inject_manager(mgr: MemoryManager) -> None:
    global _manager
    _manager = mgr


def _get_mgr() -> MemoryManager:
    if _manager is None:
        raise HTTPException(status_code=503, detail="Memory manager not initialized")
    return _manager


def _check_auth(token: str) -> None:
    expected = os.environ.get("NEXUS_DASHBOARD_TOKEN", "")
    if not expected:
        try:
            expected = Path(".nexus_token").read_text().strip()
        except (FileNotFoundError, OSError):
            pass
    if not expected:
        return
    if token != expected:
        raise HTTPException(status_code=403, detail="Invalid authentication token")


class SaveFactRequest(BaseModel):
    fact_text: str
    type: str = "semantic"
    importance_score: float = 0.5
    confidence: float = 0.5
    conversation_id: str | None = None
    message_id: str | None = None


@router.get("")
async def list_memories(token: str = Query(""), conversation_id: str | None = None):
    _check_auth(token)
    mgr = _get_mgr()
    memories = await mgr.get_all(conversation_id)
    stats = await mgr.get_stats()
    return {
        "memories": [m.model_dump(mode='json') for m in memories],
        "stats": stats.model_dump(mode='json'),
    }


@router.get("/stats")
async def memory_stats(token: str = Query("")):
    _check_auth(token)
    mgr = _get_mgr()
    stats = await mgr.get_stats()
    return stats.model_dump(mode='json')


@router.post("/save")
async def save_memory(body: SaveFactRequest, token: str = Query("")):
    _check_auth(token)
    mgr = _get_mgr()
    fact = UserFact(
        fact_text=body.fact_text,
        type=body.type,
        importance_score=body.importance_score,
        confidence=body.confidence,
        source_conversation_id=body.conversation_id,
        source_message_id=body.message_id,
    )
    saved = await mgr.save_fact(fact)
    return {"success": True, "fact": saved.model_dump(mode='json')}


@router.delete("/{memory_id}")
async def delete_memory(memory_id: str, token: str = Query("")):
    _check_auth(token)
    mgr = _get_mgr()
    success = await mgr.delete(memory_id)
    return {"success": success}


@router.post("/clear")
async def clear_memories(token: str = Query("")):
    _check_auth(token)
    mgr = _get_mgr()
    count = await mgr.clear_all()
    return {"success": True, "count": count}


@router.post("/rebuild")
async def rebuild_memories(token: str = Query(""), conversation_id: str | None = Query(None)):
    _check_auth(token)
    mgr = _get_mgr()
    rebuilt = await mgr.rebuild(conversation_id)
    return {"success": True, "rebuilt": rebuilt}


@router.post("/optimize")
async def optimize_memories(token: str = Query("")):
    _check_auth(token)
    mgr = _get_mgr()
    result = await mgr.optimize()
    return {"success": True, **result}


@router.post("/persistent/toggle")
async def toggle_persistent(token: str = Query(""), enabled: bool = Query(True)):
    _check_auth(token)
    state = set_toggle("persistent_mode", enabled)
    return {"success": True, "enabled": state["persistent_mode"]}


@router.post("/smart/toggle")
async def toggle_smart(token: str = Query(""), enabled: bool = Query(True)):
    _check_auth(token)
    state = set_toggle("smart_mode", enabled)
    return {"success": True, "enabled": state["smart_mode"]}
