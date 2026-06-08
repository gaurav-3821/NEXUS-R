"""Async SQLite database layer for MemoryManager — schema, CRUD, and connection."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import aiosqlite

from nexus_r.memory.models import BlackboardState, UserFact


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _serialize(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt is not None else None


def _deserialize(val: str | None) -> datetime | None:
    if val is None:
        return None
    try:
        return datetime.fromisoformat(val)
    except (ValueError, TypeError):
        return None


_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS user_facts (
    id                  TEXT PRIMARY KEY,
    fact_text           TEXT NOT NULL,
    importance_score    REAL NOT NULL DEFAULT 0.5,
    confidence          REAL NOT NULL DEFAULT 0.5,
    type                TEXT NOT NULL DEFAULT 'semantic',
    source_conversation_id TEXT,
    source_message_id   TEXT,
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL,
    expires_at          TEXT,
    last_referenced_at  TEXT
);

CREATE TABLE IF NOT EXISTS blackboard_states (
    conversation_id     TEXT PRIMARY KEY,
    current_task        TEXT NOT NULL DEFAULT '',
    constraints         TEXT NOT NULL DEFAULT '[]',
    progress            TEXT NOT NULL DEFAULT '',
    extracted_fact_ids  TEXT NOT NULL DEFAULT '[]',
    compressed_summary  TEXT NOT NULL DEFAULT '',
    last_model_used     TEXT NOT NULL DEFAULT '',
    token_budget        INTEGER NOT NULL DEFAULT 4096,
    chat_ring           TEXT NOT NULL DEFAULT '[]',
    updated_at          TEXT NOT NULL
);
"""


class Database:
    """Async wrapper around aiosqlite for user_facts + blackboard_states."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._conn: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        self._conn = await aiosqlite.connect(self._db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.executescript(_SCHEMA_SQL)
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None

    # ------------------------------------------------------------------
    # UserFact CRUD
    # ------------------------------------------------------------------

    async def get_all_facts(self, conversation_id: str | None = None) -> list[UserFact]:
        rows: list[aiosqlite.Row]
        if conversation_id:
            cursor = await self._conn.execute(
                "SELECT * FROM user_facts WHERE source_conversation_id = ? ORDER BY created_at",
                (conversation_id,),
            )
            rows = await cursor.fetchall()
        else:
            cursor = await self._conn.execute("SELECT * FROM user_facts ORDER BY created_at")
            rows = await cursor.fetchall()
        return [self._row_to_fact(r) for r in rows]

    async def get_fact(self, fact_id: str) -> UserFact | None:
        cursor = await self._conn.execute(
            "SELECT * FROM user_facts WHERE id = ?", (fact_id,)
        )
        row = await cursor.fetchone()
        return self._row_to_fact(row) if row else None

    async def upsert_fact(self, fact: UserFact) -> UserFact:
        now = _utcnow()
        existing = await self.get_fact(fact.id)
        if existing:
            created = existing.created_at
        else:
            created = now
        await self._conn.execute(
            """INSERT OR REPLACE INTO user_facts
               (id, fact_text, importance_score, confidence, type,
                source_conversation_id, source_message_id,
                created_at, updated_at, expires_at, last_referenced_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                fact.id,
                fact.fact_text,
                fact.importance_score,
                fact.confidence,
                fact.type,
                fact.source_conversation_id,
                fact.source_message_id,
                _serialize(created),
                _serialize(now),
                _serialize(fact.expires_at),
                _serialize(fact.last_referenced_at),
            ),
        )
        await self._conn.commit()
        fact.created_at = created
        fact.updated_at = now
        return fact

    async def upsert_facts_bulk(self, facts: list[UserFact]) -> list[UserFact]:
        saved = []
        for f in facts:
            saved.append(await self.upsert_fact(f))
        return saved

    async def delete_fact(self, fact_id: str) -> bool:
        cursor = await self._conn.execute(
            "DELETE FROM user_facts WHERE id = ?", (fact_id,)
        )
        await self._conn.commit()
        return cursor.rowcount > 0

    async def delete_all_facts(self) -> int:
        cursor = await self._conn.execute("DELETE FROM user_facts")
        await self._conn.commit()
        return cursor.rowcount

    async def delete_facts_by_ids(self, ids: set[str]) -> int:
        if not ids:
            return 0
        placeholders = ",".join("?" for _ in ids)
        cursor = await self._conn.execute(
            f"DELETE FROM user_facts WHERE id IN ({placeholders})",
            list(ids),
        )
        await self._conn.commit()
        return cursor.rowcount

    async def touch_fact(self, fact_id: str) -> bool:
        now = _serialize(_utcnow())
        cursor = await self._conn.execute(
            "UPDATE user_facts SET last_referenced_at = ?, updated_at = ? WHERE id = ?",
            (now, now, fact_id),
        )
        await self._conn.commit()
        return cursor.rowcount > 0

    # ------------------------------------------------------------------
    # BlackboardState CRUD
    # ------------------------------------------------------------------

    async def get_board(self, conversation_id: str) -> BlackboardState | None:
        cursor = await self._conn.execute(
            "SELECT * FROM blackboard_states WHERE conversation_id = ?",
            (conversation_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return self._row_to_board(row)

    async def upsert_board(self, board: BlackboardState) -> BlackboardState:
        now = _serialize(_utcnow())
        fact_ids = json.dumps([f.id for f in board.extracted_facts])
        await self._conn.execute(
            """INSERT OR REPLACE INTO blackboard_states
               (conversation_id, current_task, constraints, progress,
                extracted_fact_ids, compressed_summary, last_model_used,
                token_budget, chat_ring, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                board.conversation_id,
                board.current_task,
                json.dumps(board.constraints),
                board.progress,
                fact_ids,
                board.compressed_summary,
                board.last_model_used,
                board.token_budget,
                json.dumps(board.chat_ring),
                now,
            ),
        )
        await self._conn.commit()
        board.updated_at = _utcnow()
        return board

    async def delete_all_boards(self) -> int:
        cursor = await self._conn.execute("DELETE FROM blackboard_states")
        await self._conn.commit()
        return cursor.rowcount

    async def get_all_boards(self) -> list[BlackboardState]:
        cursor = await self._conn.execute("SELECT * FROM blackboard_states")
        rows = await cursor.fetchall()
        return [self._row_to_board(r) for r in rows]

    # ------------------------------------------------------------------
    # Row → model helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_fact(row: aiosqlite.Row) -> UserFact:
        return UserFact(
            id=row["id"],
            fact_text=row["fact_text"],
            importance_score=row["importance_score"],
            confidence=row["confidence"],
            type=row["type"],
            source_conversation_id=row["source_conversation_id"],
            source_message_id=row["source_message_id"],
            created_at=_deserialize(row["created_at"]),
            updated_at=_deserialize(row["updated_at"]),
            expires_at=_deserialize(row["expires_at"]),
            last_referenced_at=_deserialize(row["last_referenced_at"]),
        )

    @staticmethod
    def _row_to_board(row: aiosqlite.Row) -> BlackboardState:
        return BlackboardState(
            conversation_id=row["conversation_id"],
            current_task=row["current_task"],
            constraints=json.loads(row["constraints"]) if row["constraints"] else [],
            progress=row["progress"],
            extracted_facts=[],
            compressed_summary=row["compressed_summary"],
            last_model_used=row["last_model_used"],
            token_budget=row["token_budget"],
            chat_ring=json.loads(row["chat_ring"]) if row["chat_ring"] else [],
            updated_at=_deserialize(row["updated_at"]),
        )
