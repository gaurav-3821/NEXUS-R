# Open Assumptions

Assumptions are claims that may be useful but are not yet trustworthy. Do not
silently turn them into facts.

## ASM-0001: Current Delivery Phase

- Status: `Open`
- Claim: The current implemented and validated delivery phase is unclear.
- Why it matters: Task scope and audit expectations may differ by phase.
- Evidence: `README.md` claims Phase 2 validation, while
  `nexus-r/specs/00_architecture.md` still defines Phase 1 limits.
- Owner: `AUTHORITY`
- Resolution condition: Human identifies the current authoritative milestone
  and updates or supersedes stale documentation.

## ASM-0002: Minimum Supported Python Version

- Status: `Open`
- Claim: The intended minimum supported Python version is unclear.
- Why it matters: CI, local setup, and compatibility decisions depend on it.
- Evidence: `README.md` and `CONTRIBUTING.md` say Python 3.12+, while
  `nexus-r/pyproject.toml` declares `>=3.11`.
- Owner: `AUTHORITY`
- Resolution condition: Human selects the supported version policy and aligns
  package metadata and documentation.

## ASM-0003: Built Frontend Asset Policy

- Status: `Open`
- Claim: It is unclear whether built assets under
  `nexus-r/modules/web_ui/src/static/` must be committed with frontend source
  changes.
- Why it matters: Audits need to distinguish source edits from generated files
  and avoid stale deployed assets.
- Evidence: The current worktree contains changes in both `nexus-r/frontend/`
  and `nexus-r/modules/web_ui/src/static/`.
- Owner: `AUTHORITY`
- Resolution condition: Document the build and commit policy for web assets.

## Entry Template

```text
## ASM-XXXX: Short Name

- Status: Open | Verified | Rejected | Expired
- Claim:
- Why it matters:
- Evidence:
- Owner:
- Resolution condition:
```

