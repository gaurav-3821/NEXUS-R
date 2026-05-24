# Test Environment Recovery Guide

**Purpose:** Document how to recover and restore the test environment after corruption, crashes, or stale state.

## Common Issues

### 1. SQLite Database Lock
**Symptom:** `database is locked` errors in tests
**Fix:** Delete the `.test-tmp` directory and any stale WAL/SHM files:
```powershell
Remove-Item -Recurse -Force .test-tmp -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force nexus-r/.test-tmp -ErrorAction SilentlyContinue
```

### 2. Pytest Cache Corruption
**Symptom:** `PytestCacheWarning: could not create cache path`
**Fix:** Clear pytest cache:
```powershell
Remove-Item -Recurse -Force .pytest_cache -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force nexus-r/.pytest_cache -ErrorAction SilentlyContinue
```

### 3. Stale Temp Workspaces
**Symptom:** Tests fail with workspace path mismatches or leftover files
**Fix:** Clean all `.phase-*`, `.etd-*`, `.concurrency-*`, `.long-*`, `.fresh-*`, `.reproducibility-*` directories:
```powershell
Get-ChildItem -Directory -Filter ".*-*" | Remove-Item -Recurse -Force
```

### 4. Orphaned EventStore Connections
**Symptom:** `cannot open database` after test crash
**Fix:** Ensure all Orchestrator instances are closed, then remove DB:
```powershell
Remove-Item -Recurse -Force *.db *.db-wal *.db-shm -ErrorAction SilentlyContinue
```

### 5. Session Manager State Corruption
**Symptom:** Session ID mismatch or stale pointer errors
**Fix:** Clear session identity files:
```powershell
Remove-Item -Recurse -Force identity.key -ErrorAction SilentlyContinue
```

## Prevention

- Tests now use `--basetemp=.test-tmp` (configured in `pytest.ini`)
- `conftest.py` sets `TMPDIR` to a project-local `.test-tmp` directory
- All temp workspaces are created under the project root, not in system temp
- Async cleanup hooks run after test sessions

## Verification

After cleanup, verify the environment:
```powershell
pytest nexus-r/tests/ -q --tb=short
```
Expected: validation suite returns the current frozen baseline without lock or cache errors. The latest recorded baseline in `.validation_freeze.json` is `339 passed`.
