# NEXUS-R Project Orientation

## Purpose

NEXUS-R is a local-first AI agent runtime. The repository describes a modular
system for routing model requests, executing bounded tasks, persisting state,
recording traces, applying trust controls, and presenting a web UI.

This file is intentionally short. Product details belong in the specifications
and source code.

## Repository Layout

| Path | Purpose |
| --- | --- |
| `README.md` | Root project overview and validation claims |
| `ARCHITECTURE.md` | High-level target architecture |
| `CONTRIBUTING.md` | Existing development and verification conventions |
| `nexus-r/specs/` | Product specifications and acceptance criteria |
| `nexus-r/foundation/nexus_r/` | Shared Python infrastructure |
| `nexus-r/modules/` | Product modules |
| `nexus-r/tests/` | Unit, integration, security, stress, and failure tests |
| `nexus-r/frontend/` | Web frontend source |
| `nexus-r/modules/web_ui/src/static/` | Built web UI assets served by the backend |
| `.nexus-r/` | Local runtime data; ignored by Git |
| `.nexus-intel/` | AI collaboration control plane; tracked by Git |

## Existing Development Convention

`CONTRIBUTING.md` states that development should be specification-driven, that
agents work within clear boundaries, and that verification occurs before
integration. This control plane extends that approach with explicit task
contracts, audit reports, assumptions, risks, and human approvals.

## Known Documentation Questions

Some repository documents disagree about the current delivery phase and minimum
Python version. These disagreements are recorded in `ASSUMPTIONS.md`. Agents
must not resolve them silently.

