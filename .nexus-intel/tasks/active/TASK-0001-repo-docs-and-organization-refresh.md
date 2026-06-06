# TASK-0001: Repository Documentation And Organization Refresh

- Status: `Audited`
- Decision level: `RECOMMEND`
- Created: `2026-06-03`
- Coordinator: `ChatGPT`
- Implementer: `ChatGPT`
- Auditor:
- Human authority: `Gaurav`

## Goal

Refresh the repository's top-level documentation and non-code organization so
the project presents a consistent, current, high-signal overview of NEXUS-R
without changing unrelated product behavior.

## Why It Matters

The current repository mixes polished source code with stale claims, duplicate
readmes, encoding corruption, generated frontend artifacts, and many root-level
reports. That makes the project harder to understand, weaker to review, and
more likely to mislead new readers about what is implemented today.

## Non-Goals

- Do not modify the in-progress model management, router, or chat behavior that
  is already present in the worktree unless separately approved.
- Do not silently change architecture, validation claims, supported platforms,
  or release phase status where the repository already disagrees.
- Do not delete historical reports; move or index them only if the destination
  and rationale are explicit.
- Do not resolve open assumptions `ASM-0001`, `ASM-0002`, or `ASM-0003`
  without human approval.

## Relevant Context

- Specs: `nexus-r/specs/00_architecture.md`, `nexus-r/specs/99_acceptance_criteria.md`
- ADRs: `None referenced yet`
- Facts:
  - Root `README.md` contains encoding corruption and phase/traction claims.
  - `nexus-r/README.md` describes a Python + vanilla JS UI, but the repo
    contains `nexus-r/frontend/` with React 19 + Vite 8.
  - `git status` on `2026-06-03` shows unrelated source changes already in
    progress under `nexus-r/frontend/`, `nexus-r/modules/`, and tests.
  - The repo root contains many PDFs, PNGs, and reports mixed with source and
    operational files.
- Assumptions: `ASM-0001`, `ASM-0002`, `ASM-0003`
- Risks: `RISK-0001`, `RISK-0005`
- Prior failures: `None referenced yet`

## Suggested Approach

Use the smallest scope that materially improves repo clarity:

1. Inventory top-level docs, duplicate summaries, generated artifacts, and
   scratch/runtime files.
2. Rewrite the root `README.md` around verified repository structure, product
   purpose, traction evidence that can be sourced locally, and a clean quick
   start.
3. Align `ARCHITECTURE.md`, `CONTRIBUTING.md`, and `nexus-r/README.md` with the
   actual stack and layout, while avoiding unresolved phase/version claims.
4. Organize root-level non-source files into clearer documentation buckets or
   archives where approved, and tighten `.gitignore` for transient frontend
   artifacts such as `.vite/`.
5. Add a short index or navigation aid if the resulting document set still has
   many reports.

Simpler alternative:
- Only rewrite `README.md` and leave the rest of the repo untouched. This is
  lower risk but preserves structural clutter and conflicting supporting docs.

## Affected Paths

- Expected files or directories:
  - `README.md`
  - `ARCHITECTURE.md`
  - `CONTRIBUTING.md`
  - `nexus-r/README.md`
  - `docs/`
  - `.gitignore`
- Paths that must not change:
  - Existing modified product code under `nexus-r/frontend/src/`
  - Existing modified product code under `nexus-r/modules/`
  - Existing modified tests under `nexus-r/tests/`
  - `.nexus-intel/GOVERNANCE.md`

## Acceptance Criteria

| ID | Criterion | Audit status |
| --- | --- | --- |
| AC-1 | The root `README.md` is readable ASCII/UTF-8 text with no mojibake and reflects the current repository structure. | `Not Verified` |
| AC-2 | `ARCHITECTURE.md`, `CONTRIBUTING.md`, and `nexus-r/README.md` no longer contradict the verified stack and layout in obvious ways. | `Not Verified` |
| AC-3 | Repository organization for important non-code files is clearer, with a documented home for reports or an explicit index. | `Not Verified` |
| AC-4 | Transient/generated frontend workspace artifacts that should not be tracked are ignored or otherwise handled explicitly. | `Not Verified` |
| AC-5 | Unrelated in-progress source changes remain untouched by this task. | `Not Verified` |

## Required Verification

| Check | Command or manual step | Required |
| --- | --- | --- |
| Git isolation check | `git status --short --branch` before and after changes | Yes |
| Documentation consistency review | Manual compare of root docs against repo structure and package metadata | Yes |
| Python metadata check | Compare docs with `nexus-r/pyproject.toml` and record unresolved mismatch if still open | Yes |
| Frontend stack check | Compare docs with `nexus-r/frontend/package.json` and directory layout | Yes |

## Approval Questions

- Should this task be limited to documentation and repository organization, or
  do you also want the currently modified source files reviewed, cleaned up, and
  potentially rewritten in the same task?
- For `ASM-0002`, should docs align to Python `>=3.11` to match package
  metadata, or should package metadata be raised to `>=3.12`?
- For `ASM-0003`, should built assets under
  `nexus-r/modules/web_ui/src/static/` remain committed alongside frontend
  source changes?
- May historical PDFs, benchmark images, and review reports be moved out of the
  repository root into a documented archive location?

## Human Scope Approval

- Status: `Approved`
- Approved by: `Gaurav`
- Date: `2026-06-03`
- Notes: `Proceed with updating the repo and refreshing documentation; project is known to be incomplete.`

## Implementation Evidence

- Changed files:
  - `README.md`
  - `ARCHITECTURE.md`
  - `CONTRIBUTING.md`
  - `nexus-r/README.md`
  - `nexus-r/frontend/README.md`
  - `.gitignore`
  - `docs/INDEX.md`
  - `docs/reports/README.md`
  - `docs/reports/backend_readiness_audit_2026-05-31.md`
  - `.nexus-intel/tasks/active/TASK-0001-repo-docs-and-organization-refresh.md`
- Commands run:
  - `git status --short --branch`
  - `rg --files`
  - `git remote -v`
  - `git log --oneline -5`
  - `git diff --stat`
  - targeted `Get-Content` reads for root docs, package metadata, specs, module contracts, and frontend metadata
- Results:
  - Root documentation was rewritten to match the verified repo structure and remove corrupted text.
  - Package-level and frontend readmes now reflect the current Python, FastAPI, React, and Vite stack.
  - A docs index was added, and a root-level Markdown audit was moved under `docs/reports/`.
  - `.gitignore` now covers transient frontend and log artifacts such as `.vite/`, `node_modules/`, `htmlcov/`, and `*.log`.
- Unresolved risks:
  - `ASM-0001` remains open: historical phase-status documents still disagree.
  - `ASM-0003` remains open: built web assets are still committed, but the policy is not yet formally documented beyond repo notes.
  - Unrelated in-progress product code changes remain in the worktree and still require separate review.
- Implementation notes:
  - The refresh intentionally avoided edits to existing modified product code under `nexus-r/frontend/src/`, `nexus-r/modules/`, and `nexus-r/tests/`.
  - Documentation now aligns to the package metadata minimum Python version of `>=3.11`.

## Audit

- Report: `../../audits/AUDIT-TASK-0001.md`
- Verdict: `Pass With Risks`

## Human Completion Decision

- Decision: `Pending | Accepted | Rejected | Revision Requested`
- Decided by:
- Date:
- Notes:
