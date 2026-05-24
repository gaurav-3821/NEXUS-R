# Test Environment Recovery Guide

## Symptom

```
PermissionError: [WinError 5] Access is denied: 'C:\Users\<user>\AppData\Local\Temp\pytest-of-<user>'
```

This error appears when running `pytest` and prevents temp-directory-based tests from executing.

## Cause

A prior test run crashed or was force-terminated (Ctrl+C, OOM, power loss) while pytest still held file handles to its temporary directory at `%TEMP%\pytest-of-<username>`. Windows locks the directory tree until all handles are released, and a crash can orphan these locks.

Affected tests report `ERROR at setup` rather than `FAILED` because the `tmp_path` fixture cannot create temporary subdirectories.

## Manual Fix

1. Close all terminal/IDE windows that may hold handles.
2. In an **elevated (Admin) PowerShell**:
   ```powershell
   rmdir /s /q $env:TEMP\pytest-of-$env:USERNAME
   ```
3. If that fails with "Access is denied", restart the machine to release orphaned handles, then repeat step 2.
4. After cleanup, verify with:
   ```powershell
   Test-Path "$env:TEMP\pytest-of-$env:USERNAME"  # should be False
   ```
5. Open a new terminal and re-run `pytest`.

## Automated Fix (conftest.py)

The project-level `conftest.py` at `nexus-r/tests/conftest.py` now includes:

- `pytest_sessionstart` — sets `TEMP`, `TMP`, `TMPDIR` to a project-local `.test-tmp/` directory (inside the repo root), avoiding `%TEMP%` entirely.
- `pytest_sessionfinish` — force-removes `.test-tmp/` after the session ends, even if some files are locked.
- Permission-resilient cleanup — falls back to `chmod` + individual file deletion if `shutil.rmtree` fails.

This prevents the corrupted-temp issue from recurring because:
- `.test-tmp/` is project-scoped and cleaned on every session start/finish.
- No cross-session state is retained.
- Crashes only orphan a directory inside the repo, which is force-cleaned on next run.

## Prevention (Short-Term)

Run with zero retention to avoid accumulating stale temp state:

```powershell
pytest -o tmp_path_retention_count=0
```

Or set `TMPDIR` to a clean location before running:

```powershell
$env:TMPDIR = ".\test-tmp"; pytest
```

## Prevention (Long-Term)

The conftest.py hooks above make this unnecessary for normal development. If running tests outside `pytest` (e.g., directly with `python -m pytest`), ensure the virtual environment or launch script sets `TMPDIR`.

## Recovery Verification

Run the failing tests with:

```powershell
pytest tests/unit/test_session_manager.py -v
```

All tests should pass (green). If any still fail with `PermissionError`, repeat the manual fix and verify no background processes hold handles on `pytest-of-*` directories.
