from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import threading
from typing import Any
from uuid import uuid4

from nexus_r.errors import SessionPathMismatchError, SessionStateError


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonicalize_path(path: str | Path) -> str:
    return os.path.normcase(str(Path(path).resolve(strict=False)))


def _json_dumps(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


@dataclass(slots=True)
class SessionResumeResult:
    session_id: str
    rollout_id: str | None
    sequence: int
    state: dict[str, Any]
    repaired: bool = False
    repair_reasons: tuple[str, ...] = ()


class SessionManager:
    def __init__(self, workspace_root: str | Path) -> None:
        self.workspace_root = Path(workspace_root).resolve()
        self.state_dir = self.workspace_root / ".nexus-r"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.state_dir / "session_runtime.sqlite3"
        self.sessions_dir = self.state_dir / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn: sqlite3.Connection | None = None

    def initialize(self) -> None:
        if self._conn is not None:
            return
        with self._lock:
            if self._conn is not None:
                return
            conn = sqlite3.connect(self.db_path, timeout=5, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.execute("PRAGMA synchronous=FULL")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    workspace_root TEXT NOT NULL,
                    canonical_workspace_root TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_sequence INTEGER NOT NULL DEFAULT 0,
                    active_rollout_id TEXT,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    last_error TEXT
                );

                CREATE TABLE IF NOT EXISTS rollouts (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                    sequence INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    checkpoint_reason TEXT NOT NULL,
                    snapshot_relpath TEXT NOT NULL,
                    expected_hash TEXT NOT NULL,
                    parent_rollout_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    repair_note TEXT,
                    UNIQUE(session_id, sequence)
                );

                CREATE TABLE IF NOT EXISTS repair_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    rollout_id TEXT,
                    issue TEXT NOT NULL,
                    action TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS runtime_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_rollouts_session_sequence
                ON rollouts(session_id, sequence DESC);
                """
            )
            conn.commit()
            self._conn = conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def get_or_create_default_session(self) -> str:
        return self.get_or_create_session("default")

    def get_or_create_session(self, name: str, metadata: dict[str, Any] | None = None) -> str:
        self.initialize()
        with self._lock:
            conn = self._require_conn()
            canonical_root = canonicalize_path(self.workspace_root)
            row = conn.execute(
                """
                SELECT id FROM sessions
                WHERE canonical_workspace_root = ? AND name = ?
                """,
                (canonical_root, name),
            ).fetchone()
            if row:
                return str(row["id"])

            session_id = str(uuid4())
            now = utc_now()
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute(
                    """
                    INSERT INTO sessions (
                        id, name, workspace_root, canonical_workspace_root, status,
                        created_at, updated_at, last_sequence, active_rollout_id, metadata_json, last_error
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, NULL, ?, NULL)
                    """,
                    (
                        session_id,
                        name,
                        str(self.workspace_root),
                        canonical_root,
                        "idle",
                        now,
                        now,
                        _json_dumps(metadata or {}),
                    ),
                )
                conn.execute(
                    """
                    INSERT INTO runtime_state(key, value)
                    VALUES ('active_session_id', ?)
                    ON CONFLICT(key) DO UPDATE SET value = excluded.value
                    """,
                    (session_id,),
                )
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            return session_id

    def switch_active_session(self, session_id: str) -> None:
        self.initialize()
        with self._lock:
            conn = self._require_conn()
            row = conn.execute("SELECT id FROM sessions WHERE id = ?", (session_id,)).fetchone()
            if row is None:
                raise SessionStateError(f"Unknown session: {session_id}")
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute(
                    """
                    INSERT INTO runtime_state(key, value)
                    VALUES ('active_session_id', ?)
                    ON CONFLICT(key) DO UPDATE SET value = excluded.value
                    """,
                    (session_id,),
                )
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def get_active_session_id(self) -> str | None:
        self.initialize()
        conn = self._require_conn()
        row = conn.execute(
            "SELECT value FROM runtime_state WHERE key = 'active_session_id'"
        ).fetchone()
        return str(row["value"]) if row else None

    def checkpoint(
        self,
        session_id: str,
        state: dict[str, Any],
        *,
        checkpoint_reason: str,
        status: str | None = None,
        last_error: str | None = None,
    ) -> SessionResumeResult:
        self.initialize()
        payload = _json_dumps(state)
        payload_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        now = utc_now()

        with self._lock:
            conn = self._require_conn()
            session = conn.execute(
                "SELECT active_rollout_id, last_sequence FROM sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
            if session is None:
                raise SessionStateError(f"Unknown session: {session_id}")

            rollout_id = str(uuid4())
            sequence = int(session["last_sequence"]) + 1
            relpath = Path(session_id) / "rollouts" / f"{sequence:08d}-{rollout_id}.json"
            full_path = self.sessions_dir / relpath
            full_path.parent.mkdir(parents=True, exist_ok=True)

            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute(
                    """
                    INSERT INTO rollouts (
                        id, session_id, sequence, status, checkpoint_reason,
                        snapshot_relpath, expected_hash, parent_rollout_id, created_at, updated_at, repair_note
                    ) VALUES (?, ?, ?, 'preparing', ?, ?, ?, ?, ?, ?, NULL)
                    """,
                    (
                        rollout_id,
                        session_id,
                        sequence,
                        checkpoint_reason,
                        str(relpath),
                        payload_hash,
                        session["active_rollout_id"],
                        now,
                        now,
                    ),
                )
                conn.commit()
            except Exception:
                conn.rollback()
                raise

            self._atomic_write_json(full_path, payload)

            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute(
                    """
                    UPDATE rollouts
                    SET status = 'ready', updated_at = ?, repair_note = NULL
                    WHERE id = ?
                    """,
                    (utc_now(), rollout_id),
                )
                conn.execute(
                    """
                    UPDATE sessions
                    SET updated_at = ?, last_sequence = ?, active_rollout_id = ?,
                        status = COALESCE(?, status), last_error = ?
                    WHERE id = ?
                    """,
                    (utc_now(), sequence, rollout_id, status, last_error, session_id),
                )
                conn.commit()
            except Exception:
                conn.rollback()
                raise

        return SessionResumeResult(
            session_id=session_id,
            rollout_id=rollout_id,
            sequence=sequence,
            state=json.loads(payload),
        )

    def resume_session(self, session_id: str, workspace_root: str | Path | None = None) -> SessionResumeResult:
        self.initialize()
        with self._lock:
            conn = self._require_conn()
            session = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
            if session is None:
                raise SessionStateError(f"Unknown session: {session_id}")

            expected_root = str(session["canonical_workspace_root"])
            actual_root = canonicalize_path(workspace_root or self.workspace_root)
            if actual_root != expected_root:
                raise SessionPathMismatchError(
                    f"Session {session_id} belongs to {expected_root}, not {actual_root}"
                )

            if str(session["workspace_root"]) != str(self.workspace_root):
                conn.execute("BEGIN IMMEDIATE")
                try:
                    conn.execute(
                        "UPDATE sessions SET workspace_root = ?, updated_at = ? WHERE id = ?",
                        (str(self.workspace_root), utc_now(), session_id),
                    )
                    conn.commit()
                except Exception:
                    conn.rollback()
                    raise

            repaired, repair_reasons = self._repair_locked(session_id)
            session = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
            rollout_id = session["active_rollout_id"]
            if rollout_id is None:
                return SessionResumeResult(
                    session_id=session_id,
                    rollout_id=None,
                    sequence=0,
                    state={},
                    repaired=repaired,
                    repair_reasons=tuple(repair_reasons),
                )
            rollout = conn.execute("SELECT * FROM rollouts WHERE id = ?", (rollout_id,)).fetchone()
            if rollout is None:
                raise SessionStateError(f"Session {session_id} points to missing rollout metadata.")
            state = self._load_snapshot(rollout)
            return SessionResumeResult(
                session_id=session_id,
                rollout_id=str(rollout["id"]),
                sequence=int(rollout["sequence"]),
                state=state,
                repaired=repaired,
                repair_reasons=tuple(repair_reasons),
            )

    def inspect_session(self, session_id: str) -> dict[str, Any]:
        self.initialize()
        conn = self._require_conn()
        session = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if session is None:
            raise SessionStateError(f"Unknown session: {session_id}")
        return dict(session)

    def list_rollouts(self, session_id: str) -> list[dict[str, Any]]:
        self.initialize()
        conn = self._require_conn()
        rows = conn.execute(
            "SELECT * FROM rollouts WHERE session_id = ? ORDER BY sequence ASC",
            (session_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def get_repair_log(self, session_id: str) -> list[dict[str, Any]]:
        self.initialize()
        conn = self._require_conn()
        rows = conn.execute(
            "SELECT * FROM repair_log WHERE session_id = ? ORDER BY id ASC",
            (session_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def _repair_locked(self, session_id: str) -> tuple[bool, list[str]]:
        conn = self._require_conn()
        session = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        rollouts = conn.execute(
            "SELECT * FROM rollouts WHERE session_id = ? ORDER BY sequence DESC",
            (session_id,),
        ).fetchall()

        latest_ready_id: str | None = None
        repair_reasons: list[str] = []

        for rollout in rollouts:
            rollout_id = str(rollout["id"])
            state = str(rollout["status"])
            validation = self._validate_rollout(rollout)
            if state == "preparing":
                if validation == "valid":
                    self._update_rollout_status(
                        rollout_id,
                        "ready",
                        "promoted_preparing_rollout",
                        "Promoted preparing rollout after crash-safe snapshot validation.",
                    )
                    repair_reasons.append("promoted_preparing_rollout")
                    latest_ready_id = latest_ready_id or rollout_id
                else:
                    self._update_rollout_status(
                        rollout_id,
                        "abandoned",
                        "abandoned_partial_rollout",
                        "Marked preparing rollout abandoned because snapshot was missing or invalid.",
                    )
                    repair_reasons.append("abandoned_partial_rollout")
            elif state == "ready":
                if validation == "valid" and latest_ready_id is None:
                    latest_ready_id = rollout_id
                elif validation != "valid":
                    self._update_rollout_status(
                        rollout_id,
                        "corrupted",
                        "corrupted_ready_rollout",
                        "Marked ready rollout corrupted because snapshot hash or file content failed validation.",
                    )
                    repair_reasons.append("corrupted_ready_rollout")

        current_active = str(session["active_rollout_id"]) if session["active_rollout_id"] else None
        needs_pointer_repair = current_active != latest_ready_id
        if needs_pointer_repair:
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute(
                    """
                    UPDATE sessions
                    SET active_rollout_id = ?, updated_at = ?, status = CASE
                        WHEN ? IS NULL THEN 'degraded'
                        ELSE status
                    END
                    WHERE id = ?
                    """,
                    (latest_ready_id, utc_now(), latest_ready_id, session_id),
                )
                if current_active and latest_ready_id:
                    self._log_repair(
                        session_id,
                        current_active,
                        "stale_active_pointer",
                        f"Repointed active rollout to {latest_ready_id}.",
                    )
                    repair_reasons.append("stale_active_pointer")
                elif current_active and latest_ready_id is None:
                    self._log_repair(
                        session_id,
                        current_active,
                        "lost_active_pointer",
                        "Cleared active rollout because no valid snapshot could be recovered.",
                    )
                    repair_reasons.append("lost_active_pointer")
                conn.commit()
            except Exception:
                conn.rollback()
                raise

        return (len(repair_reasons) > 0, repair_reasons)

    def _validate_rollout(self, rollout: sqlite3.Row) -> str:
        path = self.sessions_dir / str(rollout["snapshot_relpath"])
        if not path.exists():
            return "missing"
        try:
            payload = path.read_text(encoding="utf-8")
            json.loads(payload)
        except Exception:
            return "invalid_json"
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return "valid" if digest == str(rollout["expected_hash"]) else "hash_mismatch"

    def _load_snapshot(self, rollout: sqlite3.Row) -> dict[str, Any]:
        path = self.sessions_dir / str(rollout["snapshot_relpath"])
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise SessionStateError(f"Missing snapshot file: {path}") from exc
        except json.JSONDecodeError as exc:
            raise SessionStateError(f"Corrupted snapshot file: {path}") from exc

    def _update_rollout_status(self, rollout_id: str, status: str, issue: str, action: str) -> None:
        conn = self._require_conn()
        rollout = conn.execute("SELECT session_id FROM rollouts WHERE id = ?", (rollout_id,)).fetchone()
        if rollout is None:
            return
        conn.execute("BEGIN IMMEDIATE")
        try:
            conn.execute(
                "UPDATE rollouts SET status = ?, updated_at = ?, repair_note = ? WHERE id = ?",
                (status, utc_now(), action, rollout_id),
            )
            self._log_repair(str(rollout["session_id"]), rollout_id, issue, action)
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def _log_repair(self, session_id: str, rollout_id: str | None, issue: str, action: str) -> None:
        conn = self._require_conn()
        conn.execute(
            """
            INSERT INTO repair_log(session_id, rollout_id, issue, action, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, rollout_id, issue, action, utc_now()),
        )

    def _atomic_write_json(self, path: Path, payload: str) -> None:
        tmp_path = path.with_suffix(path.suffix + f".tmp-{uuid4().hex}")
        with open(tmp_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
        try:
            dir_fd = os.open(str(path.parent), os.O_RDONLY)
        except OSError:
            return
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)

    def _require_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise SessionStateError("Session manager is not initialized.")
        return self._conn
