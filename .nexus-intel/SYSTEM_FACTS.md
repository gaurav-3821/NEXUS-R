# Verified System Facts

Only promote a claim here when repository evidence supports it. Keep entries
short and link to the evidence. If a claim becomes stale, mark it `Superseded`
instead of deleting it.

## FACT-0001: Product Source Directory

- Status: `Verified`
- Checked: `2026-06-02`
- Claim: The main product source tree is under `nexus-r/`.
- Evidence: `nexus-r/pyproject.toml`, `nexus-r/modules/`, `nexus-r/tests/`

## FACT-0002: Formal Specification Directory

- Status: `Verified`
- Checked: `2026-06-02`
- Claim: Product specifications and Phase 1 acceptance criteria exist under
  `nexus-r/specs/`.
- Evidence: `nexus-r/specs/00_architecture.md`,
  `nexus-r/specs/99_acceptance_criteria.md`

## FACT-0003: Test Categories

- Status: `Verified`
- Checked: `2026-06-02`
- Claim: The repository contains unit, integration, security, stress, and
  failure test directories.
- Evidence: `nexus-r/tests/`

## FACT-0004: Python Package Metadata

- Status: `Verified`
- Checked: `2026-06-02`
- Claim: `nexus-r/pyproject.toml` declares project version `0.1.0` and Python
  requirement `>=3.11`.
- Evidence: `nexus-r/pyproject.toml`

## FACT-0005: Local Runtime Data

- Status: `Verified`
- Checked: `2026-06-02`
- Claim: `.nexus-r/` is ignored by Git and is intended for local runtime data.
- Evidence: `.gitignore`, `.nexus-r/`

## Entry Template

```text
## FACT-XXXX: Short Name

- Status: Verified | Superseded
- Checked: YYYY-MM-DD
- Claim:
- Evidence:
```

