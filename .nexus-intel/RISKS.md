# Active Risks

## RISK-0001: Documentation Drift

- Status: `Open`
- Risk: Conflicting documentation may cause agents to implement against stale
  requirements.
- Mitigation: Use task-specific spec references. Record disagreements in
  `ASSUMPTIONS.md`. Require human resolution when a disagreement affects scope.

## RISK-0002: Audit Contamination

- Status: `Open`
- Risk: An auditor may repeat the implementer's explanation instead of
  independently checking behavior.
- Mitigation: Auditor reads acceptance criteria and inspects the diff before
  reading implementation notes.

## RISK-0003: Context Overload

- Status: `Open`
- Risk: Loading every historical report may crowd out relevant evidence and
  increase hallucinations.
- Mitigation: Use the bounded context packet defined in `GOVERNANCE.md`.

## RISK-0004: Local Data or Secret Leakage

- Status: `Open`
- Risk: Runtime databases, logs, identity material, or credentials may be
  copied into Git-tracked intelligence files.
- Mitigation: Never store secrets or runtime traces in `.nexus-intel/`. Keep
  `.nexus-r/` ignored. Review diffs before commits.

## RISK-0005: Overlapping Worktree Changes

- Status: `Open`
- Risk: An agent may overwrite unrelated in-progress changes already present in
  the worktree.
- Mitigation: Run `git status` before work, define affected paths in each task,
  and leave unrelated changes untouched.

## Entry Template

```text
## RISK-XXXX: Short Name

- Status: Open | Mitigated | Accepted | Closed
- Risk:
- Mitigation:
- Owner:
- Related tasks:
```

