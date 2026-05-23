# NEXUS-R Architecture

**Five subsystems. Six modules. One cross-cutting layer. No orchestration theater.**

## Design Principles

1.  **Event-sourced everything** — Every state change is an immutable event. The Event Store is the single source of truth.
2.  **MCP everywhere** — All tool integrations via Model Context Protocol. No custom connectors.
3.  **LiteLLM for model abstraction** — Unified interface for 100+ providers. We do not build our own provider router.
4.  **Deny-first security** — ML risk classifier embedded in execution. Default is deny; allow is earned.
5.  **Privacy as hard constraint** — Local models always preferred when privacy flag set. Not a preference.
6.  **Explicit generalization bounds** — No workflow applied without >90% proven success rate.
7.  **CPC short-circuit before routing** — Check cache first. Primary cost-saving mechanism.
8.  **Inline verification** — Each step has a verify phase. Catches errors at point of occurrence.

---

## Subsystem Overview

| # | Subsystem | Module | Key Responsibilities |
| :--- | :--- | :--- | :--- |
| **1** | **Input Gateway** | Intent Parser | Intent classification, confidence estimation, parameter extraction, complexity scoring (T1–T4) |
| **2** | **Cognition Router** | ISE + CAR | Capability profiling, Pareto routing (cost × latency × privacy), CPC short-circuit, adaptive fallback, quality tracking |
| **3** | **Execution Sandbox** | Execution Engine | Sandboxed agent loop via MCP, inline verification, ML risk classification, permission tiers 1–4, event-sourced traces |
| **4** | **State Core** | Memory Store | Event log (append-only), 3-tier memory (volatile / durable / identity), causal chaining, vector embeddings, projected views |
| **5** | **Workflow Engine** | CPC / ETD | Trace recording, distillation, generalization verification (>90%), parameterization, conservative application (>85%), invalidation |
| **—** | **Trust Layer** | — *(cross-cutting)* | Permission enforcement, sandbox isolation, audit log, cost dashboard, rollback, secret handling |

### Data Flow

```text
User Input
  ↓
[Input Gateway] → IntentResult (type, confidence, tier, parameters)
  ↓
[Cognition Router] → CPC Check → Cache hit? → Execute ETD (fast, cheap)
  ↓ Cache miss
[CAR] → Route to optimal model (local/BYOK) based on tier, privacy, cost cap
  ↓
[Execution Sandbox] → MCP tool loop with inline verification
  ↓
[State Core] → Log every action as immutable CausalEvent
  ↓
[Workflow Engine] → Record trace → Distill → Verify generalization → Cache ETD
  ↓
Result + Cost + Audit ID
```

---

## Key Subsystem Details

### 1. Input Gateway
**Responsibility:** Transform natural language into structured intent.

**Complexity Scoring (T1–T4):**
*   **Reasoning depth (40%)**: Logical connectors, ambiguity, planning need
*   **Knowledge breadth (30%)**: Domain specificity, recency requirements
*   **Tool complexity (30%)**: Number/type of tools, irreversibility

### 2. Cognition Router (CAR)
**Responsibility:** Select the optimal model and execution path.
1.  **CPC Check** — Query ETD cache. If similarity >85% and success rate >90%, execute cached workflow at $0.
2.  **Task Classification** — Score reasoning depth, knowledge breadth, tool complexity → composite T1–T4 tier.
3.  **Capability Profiling** — Each model maintains dynamic scores, latency percentiles, cost, privacy level.
4.  **Multi-Objective Routing** — Optimize across capability match, latency, cost, privacy (hard constraint).
5.  **Adaptive Fallback Chain** — 6 tiers: `local_7b` → `local_14b` → `local_70b` → `BYOK_budget` → `BYOK_frontier` → `managed_premium`.
6.  **Parallel Probe** — When uncertain, send to T1+T2 simultaneously.
7.  **De-escalation Learning** — Update classifier if T1 consistently handles T2-classified tasks.

### 3. Execution Sandbox
**Responsibility:** Safely execute tool invocations with verification.
*   **Terminal:** Docker container with workspace mount only.
*   **Filesystem:** Scoped to workspace directory. Parent directory traversal blocked.
*   **Browser (Phase 3):** Isolated Chromium via Playwright. No host filesystem.
*   **API calls:** Domain whitelisting. Credential injection via SecretRegistry.

**Permission tiers:**
*   **T1:** Read files, read-only terminal, web search, safe MCP *(Auto)*
*   **T2:** Write workspace files, sandboxed terminal, HTTP GET approved *(Auto + log)*
*   **T3:** Arbitrary terminal, external files, HTTP POST/PUT/DELETE, API keys *(User prompt)*
*   **T4:** Delete files, access secrets, deploy to prod, financial transactions *(Explicit confirm + reason)*

### 4. State Core (Three-Tier Memory)
*The Event Store is the single source of truth. All other memory tiers are derived views.*

1.  **Volatile (Working State):** Current task context, active plan, tool results. *(Dies when task completes)*
2.  **Durable (Event Store):** Immutable log of all actions, decisions, outcomes. *(Append-only, SQLite)*
3.  **Identity (User Profile):** Preferences, tool configs, API key refs, classifier weights. *(Encrypted file)*

**Key features:** Causal chaining (`parent_event_id`), Vector embeddings, Projected views, Compaction.

### 5. Workflow Engine (ETD)
**Core innovation:** Execution Trace Distillation with verified generalization bounds.

**Seven-Stage Pipeline:**
1.  **Trace Recording** — Sandbox logs every step.
2.  **Distillation** — Extract minimal causal chain. Drop dead-ends/retries.
3.  **Generalization Verification** — Test on held-out variants. Admit only if >90% success.
4.  **Parameterization** — Replace concrete values with typed slots.
5.  **Retrieval** — Cosine similarity + context gating + ranking.
6.  **Conservative Application** — Opt-in. Environment match required.
7.  **Invalidation** — Degrade if failure rate >30%.

---

## Research Positioning
**NEXUS-R ETD novelty claim:** *Execution trace distillation with verified generalization bounds for autonomous workflow reuse.*

| Prior Art | What They Do | What NEXUS-R Adds |
| :--- | :--- | :--- |
| **FlowMind** | Distill traces to structured workflows | Explicit generalization verification with quantified bounds |
| **Shepherd** | Per-step snapshots, trajectory compression | Conservative application + causal chaining for provenance |
| **OpenHands** | 2× cost reduction via summarization | Reusable execution plans (parameterized templates) |
| **Deep Memory** | 71% token reduction via compression | Workflow reuse (structural templates with verification) |

---

> **The architecture is intentionally flat** — no hierarchical coordination, no orchestration layers, no message buses. Each subsystem communicates through the Event Store. This eliminates synchronization complexity and enables each subsystem to be developed, tested, and deployed independently.
