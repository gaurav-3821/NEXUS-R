# Contributing To NEXUS-R

NEXUS-R is developed as a modular runtime with a tracked AI-collaboration layer
in `.nexus-intel/`. Contributions should preserve that modularity, keep changes
bounded, and avoid mixing unrelated work into a single update.

## Before You Change Code

1. Read the relevant spec under `nexus-r/specs/`.
2. Check `git status` and confirm whether the worktree already contains active
   changes.
3. Limit your change to one coherent scope.
4. Prefer updating tests and docs alongside behavior changes.

## Repository Layout

```text
NEXUS-R/
|- .nexus-intel/              AI task, governance, and audit records
|- docs/                      reports, exports, plans, and reference material
|- nexus-r/
|  |- foundation/nexus_r/     shared runtime primitives
|  |- modules/                runtime subsystems
|  |- frontend/               React + TypeScript + Vite UI source
|  |- specs/                  product and subsystem specifications
|  |- tests/                  unit, integration, security, stress, and failure tests
|  |- scripts/                validation and benchmark helpers
|  |- pyproject.toml          package metadata and dependencies
|- README.md                  root overview
|- ARCHITECTURE.md            repo architecture overview
```

## Setup

```bash
git clone https://github.com/gaurav-3821/NEXUS-R.git
cd NEXUS-R/nexus-r
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

Current package metadata requires Python `>=3.11`.

## Common Commands

```bash
pytest tests/unit -v
pytest tests/integration -v
pytest tests/security -v
pytest tests/stress -v
pytest tests/failure -v
```

Frontend source:

```bash
cd frontend
npm install
npm run dev
```

Frontend production build:

```bash
cd frontend
npm run build
```

## Contribution Rules

- Keep product code, generated assets, and documentation changes logically
  grouped.
- Do not silently rewrite unrelated files already modified in the worktree.
- If a doc claim conflicts with package metadata or tests, update the doc or
  call out the mismatch explicitly.
- Treat generated reports and exported PDFs as reference artifacts, not as the
  primary source of truth.
- Prefer small, reviewable diffs over broad rewrites.

## Documentation Expectations

Update these when relevant:

- `README.md` for repo-facing changes
- `ARCHITECTURE.md` when module boundaries or stack assumptions change
- `nexus-r/README.md` for package-level workflow and structure changes
- `docs/INDEX.md` when adding or relocating major reports

## AI-Assisted Workflow

The repo includes explicit coordination files under `.nexus-intel/`.

- Read `.nexus-intel/README.md` and `.nexus-intel/GOVERNANCE.md` before major
  AI-assisted work.
- Use a bounded task file instead of mixing planning, implementation, and audit
  into one uncontrolled change.
- Do not treat AI-generated summaries as verified facts without source or test
  support.
