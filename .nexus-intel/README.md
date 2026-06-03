# NEXUS-R Project Intelligence

This directory is the Git-tracked coordination layer for AI-assisted
development. It helps ChatGPT, Antigravity, OpenCode, and future tools exchange
reliable context without trusting conversation history.

It does not replace source code, product specifications, Git history, tests, or
human judgment.

## Start Here

For every new task:

1. Read `GOVERNANCE.md`.
2. Read the relevant role in `AGENTS.md`.
3. Read `PROJECT.md`.
4. Read `context/CURRENT_STATE.md` for orientation only.
5. Create one task file from `tasks/TASK-TEMPLATE.md`.
6. Put the approved task in `tasks/active/`.
7. Reference only the relevant facts, assumptions, risks, failures, and ADRs.
8. Require an independent report from `audits/AUDIT-TEMPLATE.md`.
9. Move the task to `tasks/completed/` only after human acceptance.

## What Is Authoritative?

Use each source for its intended purpose:

| Question | Preferred source |
| --- | --- |
| What should the product do? | Human-approved specs and ADRs |
| What does the code currently do? | Source inspection and runtime evidence |
| Did this change work? | Independent test and audit evidence |
| What is still uncertain? | `ASSUMPTIONS.md` and `RISKS.md` |
| What should an agent read first? | The active task contract |

If sources disagree, do not guess. Record the disagreement in `ASSUMPTIONS.md`
and ask the human to resolve it when the answer affects the task.

## Directory Map

| Path | Purpose |
| --- | --- |
| `GOVERNANCE.md` | Authority, safety, and workflow rules |
| `PROJECT.md` | Short stable project orientation |
| `AGENTS.md` | Replaceable roles and copy-paste startup prompts |
| `SYSTEM_FACTS.md` | Claims verified against repository evidence |
| `ASSUMPTIONS.md` | Unresolved claims that must not become silent facts |
| `RISKS.md` | Active collaboration and project risks |
| `FAILURES.md` | Reusable lessons from verified failures |
| `context/CURRENT_STATE.md` | Short disposable status cache |
| `tasks/` | Approved work contracts and completion evidence |
| `audits/` | Independent verification reports |
| `decisions/` | Human-approved Architecture Decision Records (ADRs) |

## Simple Human Workflow

1. Tell the `COORDINATOR` what you want to build.
2. Review the task contract in simple language.
3. Approve the task scope.
4. Give the approved task to the `IMPLEMENTER`.
5. Give the completed task and Git diff to the `AUDITOR`.
6. Read the audit result.
7. Accept, reject, or request revision.

Start manually. Automate repetitive checks only after this workflow has been
used successfully on several real tasks.

