from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sqlite3

import pytest

from foundation.nexus_r.errors import SessionPathMismatchError
from modules.session_manager.src.manager import SessionManager, canonicalize_path


def test_session_manager_checkpoints_and_resumes(workspace) -> None:
    manager = SessionManager(workspace)
    session_id = manager.get_or_create_default_session()
    manager.checkpoint(
        session_id,
        {"working_state": {"latest_task_id": "t1", "completed_tasks": {"t1": {"status": "running"}}}},
        checkpoint_reason="task_started",
        status="running",
    )

    resume = manager.resume_session(session_id, workspace)
    assert resume.sequence == 1
    assert resume.state["working_state"]["latest_task_id"] == "t1"
    manager.close()


def test_session_manager_repairs_stale_pointer_to_latest_valid_rollout(workspace) -> None:
    manager = SessionManager(workspace)
    session_id = manager.get_or_create_default_session()
    first = manager.checkpoint(session_id, {"working_state": {"latest_task_id": "t1"}}, checkpoint_reason="a", status="running")
    second = manager.checkpoint(session_id, {"working_state": {"latest_task_id": "t2"}}, checkpoint_reason="b", status="running")

    second_row = manager.list_rollouts(session_id)[-1]
    broken_path = manager.sessions_dir / second_row["snapshot_relpath"]
    broken_path.unlink()

    resume = manager.resume_session(session_id, workspace)
    assert resume.rollout_id == first.rollout_id
    assert "corrupted_ready_rollout" in resume.repair_reasons
    assert "stale_active_pointer" in resume.repair_reasons
    manager.close()


def test_session_manager_promotes_valid_preparing_rollout_after_crash(workspace) -> None:
    manager = SessionManager(workspace)
    session_id = manager.get_or_create_default_session()
    base = manager.checkpoint(session_id, {"working_state": {"latest_task_id": "base"}}, checkpoint_reason="base", status="running")

    conn = sqlite3.connect(manager.db_path)
    conn.row_factory = sqlite3.Row
    rollout_id = "manual-rollout"
    relpath = Path(session_id) / "rollouts" / f"{2:08d}-{rollout_id}.json"
    payload = json.dumps({"working_state": {"latest_task_id": "recovered"}}, sort_keys=True, separators=(",", ":"))
    digest = __import__("hashlib").sha256(payload.encode("utf-8")).hexdigest()
    snapshot_path = manager.sessions_dir / relpath
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(payload, encoding="utf-8")
    conn.execute(
        """
        INSERT INTO rollouts (
            id, session_id, sequence, status, checkpoint_reason, snapshot_relpath,
            expected_hash, parent_rollout_id, created_at, updated_at, repair_note
        ) VALUES (?, ?, 2, 'preparing', 'crash_window', ?, ?, ?, '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00', NULL)
        """,
        (rollout_id, session_id, str(relpath), digest, base.rollout_id),
    )
    conn.commit()
    conn.close()

    resume = manager.resume_session(session_id, workspace)
    assert resume.sequence == 2
    assert resume.state["working_state"]["latest_task_id"] == "recovered"
    assert "promoted_preparing_rollout" in resume.repair_reasons
    manager.close()


def test_session_manager_detects_workspace_path_mismatch(workspace, tmp_path) -> None:
    manager = SessionManager(workspace)
    session_id = manager.get_or_create_default_session()
    with pytest.raises(SessionPathMismatchError):
        manager.resume_session(session_id, tmp_path / "different")
    manager.close()


def test_session_manager_serializes_concurrent_checkpoints(workspace) -> None:
    manager = SessionManager(workspace)
    session_id = manager.get_or_create_default_session()

    def write_checkpoint(index: int) -> int:
        result = manager.checkpoint(
            session_id,
            {"working_state": {"latest_task_id": f"task-{index}"}},
            checkpoint_reason=f"checkpoint-{index}",
            status="running",
        )
        return result.sequence

    with ThreadPoolExecutor(max_workers=4) as executor:
        sequences = sorted(executor.map(write_checkpoint, range(12)))

    assert sequences == list(range(1, 13))
    resume = manager.resume_session(session_id, workspace)
    assert resume.sequence == 12
    manager.close()


def test_session_manager_allows_concurrent_resumes(workspace) -> None:
    manager = SessionManager(workspace)
    session_id = manager.get_or_create_default_session()
    manager.checkpoint(
        session_id,
        {"working_state": {"latest_task_id": "stable"}},
        checkpoint_reason="stable",
        status="idle",
    )

    def resume_latest() -> tuple[int, str]:
        result = manager.resume_session(session_id, workspace)
        return result.sequence, result.state["working_state"]["latest_task_id"]

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(lambda _: resume_latest(), range(20)))

    assert all(sequence == 1 for sequence, _ in results)
    assert all(task_id == "stable" for _, task_id in results)
    manager.close()


def test_session_manager_switches_between_multiple_sessions(workspace) -> None:
    manager = SessionManager(workspace)
    first = manager.get_or_create_session("alpha")
    second = manager.get_or_create_session("beta")
    manager.switch_active_session(first)
    assert manager.get_active_session_id() == first
    manager.switch_active_session(second)
    assert manager.get_active_session_id() == second
    manager.close()


def test_canonicalize_path_normalizes_equivalent_paths(workspace) -> None:
    assert canonicalize_path(workspace) == canonicalize_path(workspace / "." / "src" / "..")
