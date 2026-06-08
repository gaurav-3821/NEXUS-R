# NEXUS-R — Capabilities Overview

> A comprehensive walkthrough of every feature, configuration option, and integration point.

---

## Table of Contents

- [Model Providers](#model-providers)
- [Cognition Router (Auto-Routing)](#cognition-router-auto-routing)
- [Permission Tiers (T1–T5)](#permission-tiers-t1t5)
- [Memory & Persistence](#memory--persistence)
- [Web Dashboard](#web-dashboard)
- [CLI Reference](#cli-reference)
- [Docker Deployment](#docker-deployment)
- [Configuration](#configuration)
- [Security](#security)
- [Integrations](#integrations)

---

## Model Providers

NEXUS-R supports **10+ AI providers** through LiteLLM. Each provider can be configured independently with its own API key, model, and cost parameters.

| Provider | Type | Configuration |
|----------|------|---------------|
| **Ollama** | Local | Auto-detected. Pull models via `ollama pull`. |
| **OpenAI** | Cloud | `NEXUS_OPENAI_API_KEY` env var |
| **Anthropic** | Cloud | `NEXUS_ANTHROPIC_API_KEY` env var |
| **OpenRouter** | Cloud | `NEXUS_OPENROUTER_API_KEY` env var |
| **Groq** | Cloud | `NEXUS_GROQ_API_KEY` env var |
| **Google (Gemini)** | Cloud | `NEXUS_GOOGLE_API_KEY` env var |
| **Cohere** | Cloud | `NEXUS_COHERE_API_KEY` env var |
| **Mistral** | Cloud | `NEXUS_MISTRAL_API_KEY` env var |
| **Together AI** | Cloud | `NEXUS_TOGETHER_API_KEY` env var |
| **BYOK (Bring Your Own Key)** | Cloud | Generic provider — any OpenAI-compatible API |

### How provider selection works

1. User selects a model in the dashboard (or CLI accepts `--model`)
2. If model is `auto`, the **Cognition Router** classifies the task
3. The router picks the best provider + model combination
4. If the selected model fails (404, timeout), the next provider in the chain is tried automatically

### Local model auto-detection

When Ollama is running, NEXUS-R automatically detects installed models. GGUF files and custom model paths are normalized so the router finds them correctly.

---

## Cognition Router (Auto-Routing)

The `route_query()` engine is the decision-making core. It classifies every task in **under 1 millisecond**.

### Classification flow

```
Task Text
    │
    ├── Trivial check (≤3 words, greetings) → T1 (local)
    │
    ├── Code detection
    │   ├── ```code blocks → T2 (coder model)
    │   └── 2+ code keywords → T2 (coder model)
    │
    ├── Math detection
    │   └── 1+ math keywords → T2 (reasoning model)
    │
    ├── Cloud-needed detection
    │   ├── 2+ cloud keywords → T3/T4 (cloud provider)
    │   ├── Long + code → T3/T4 (cloud provider)
    │   └── 80+ words → T4 (cloud provider)
    │
    └── Default → T1 (local model)
              ↓
    If keyword match is inconclusive:
         → Semantic embedding (sentence-transformers)
         → Compare against anchor categories
         → Pick closest match (confidence threshold 0.40)
```

### Semantic categories

When keywords aren't enough, the router falls back to embedding similarity:

| Category | Model Keyword | Default Model |
|----------|--------------|---------------|
| Coding | `qwen2.5-coder`, `antigravity-coder` | Coder model |
| Reasoning | `deepseek-r1` | Reasoning model |
| General | `gemma2`, `llama3.2` | Chat model |

### Provider fallback chain

If the router's chosen model fails to respond:
1. Next available local model is tried
2. If no local models work, cloud provider chain is tried
3. If everything fails, a clear error message is returned

---

## Permission Tiers (T1–T5)

Every task routed through NEXUS-R is assigned a permission tier. Tiers determine what the model can do and whether explicit approval is needed.

| Tier | Label | Examples | Routing | Approval |
|------|-------|----------|---------|----------|
| **T1** | Trivial | Greetings, simple Q&A, acknowledgments | Local model | None needed |
| **T2** | Standard | Code generation, debugging, explanations | Coder/reasoning model | None needed |
| **T3** | Enhanced | Research, web search, data analysis | Cloud provider | None needed |
| **T4** | Complex | System audit, security analysis, production changes | Premium cloud | Optional |
| **T5** | Critical | Destructive operations, data deletion | Requires approval | **Required** |

---

## Memory & Persistence

### SQLite (relational)
- Conversations, user settings, model configurations
- Crash-safe via aiosqlite
- Location: `~/.nexus/` directory

### ChromaDB (vectors)
- Semantic memory search
- "What did we talk about regarding X?"
- Automatic embedding on conversation save
- Optional — app works without it

### Memory features
- Conversation ring buffer (last 3 user + 3 assistant turns)
- Semantic fact retrieval from past conversations
- Conversation history browser in the dashboard

---

## Web Dashboard

Built with **React 19 + TypeScript + Vite + Tailwind CSS v4**.

### Pages

| Page | Features |
|------|----------|
| **Chat** | Real-time streaming, model selector, conversation history, LaTeX rendering |
| **Models** | Browse available models, download new ones, set defaults |
| **Settings** | Providers, API keys, memory toggles, theme customization |
| **Appearance** | Light/dark mode, 6 accent colors |

### Key UI components

- **Sidebar** — Collapsible, conversation list, new chat button
- **Model badge** — Shows current model and routing tier per message
- **Router Decision widget** — Displays tier, estimated cost, model name
- **Memory panel** — Shows relevant past conversations
- **Cost analytics** — Per-conversation cost breakdown

### Real-time features

- WebSocket streaming for model responses
- Live cost tracking as tokens arrive
- Instant model switching without page reload

---

## CLI Reference

```bash
nexus run "<task>"              # Execute a task
nexus run "<task>" --model auto  # Let router decide (default)
nexus run "<task>" --model ollama/llama3.2  # Force specific model

nexus history                   # View conversation history
nexus cost                      # View cost summary
nexus config                    # View/edit configuration
nexus config set key value      # Update a config value
nexus dashboard start           # Start the web dashboard
```

---

## Docker Deployment

```bash
# Start everything
make docker-up

# Services
# - Backend API:  http://localhost:8000
# - Frontend:     http://localhost:3000
# - ChromaDB:     http://localhost:8001

# Stop
make docker-down

# Rebuild
make docker-build
```

Docker Compose includes:
- **Backend** — Python 3.12, FastAPI (multi-stage, ~180MB)
- **Frontend** — Nginx-served React SPA (~50MB)
- **ChromaDB** — Vector store service
- **Nginx** — Reverse proxy with WebSocket support, security headers

---

## Configuration

### Environment variables

| Variable | Purpose |
|----------|---------|
| `NEXUS_OPENAI_API_KEY` | OpenAI API key |
| `NEXUS_ANTHROPIC_API_KEY` | Anthropic API key |
| `NEXUS_OPENROUTER_API_KEY` | OpenRouter API key |
| `NEXUS_GROQ_API_KEY` | Groq API key |
| `NEXUS_GOOGLE_API_KEY` | Google AI API key |
| `NEXUS_COHERE_API_KEY` | Cohere API key |
| `NEXUS_MISTRAL_API_KEY` | Mistral API key |
| `NEXUS_TOGETHER_API_KEY` | Together AI API key |
| `NEXUS_BYOK_API_KEY` | Custom provider API key |

### Config file

Location: `~/.nexus/config.json` or local `.env`

```json
{
  "models": {
    "local_model": "auto",
    "local_api_base": "http://localhost:11434",
    "byok_model": "",
    "byok_api_base": ""
  },
  "routing": {
    "default_tier": "T1",
    "enable_semantic": true,
    "cloud_threshold": 0.6
  },
  "memory": {
    "enable_vector_store": true,
    "max_history_turns": 10,
    "chroma_db_path": "./chroma_db"
  },
  "ui": {
    "theme": "dark",
    "accent_color": "indigo"
  }
}
```

---

## Security

### Data privacy
- All data stays on your machine unless you explicitly route to a cloud provider
- No telemetry, no usage tracking, no external calls without consent
- API keys stored in environment variables or OS keyring (never in code)

### Network
- Backend binds to `127.0.0.1:8000` by default (localhost only)
- Nginx in Docker adds security headers (CSP, HSTS, X-Frame-Options)
- WebSocket connections use the same origin

### Audit
- Every routing decision is logged with timestamp, tier, model, cost, and rationale
- Append-only event store (no deletion, no modification)
- Full conversation history persisted in SQLite

### BYOK security
- API keys are never stored by NEXUS-R — only referenced from env vars
- The frontend sends keys as query parameters (over HTTPS)
- No key persistence in databases or config files

---

## Integrations

### Current
- **Ollama** — Auto-detected local models
- **10+ cloud providers** — Via LiteLLM
- **ChromaDB** — Vector memory store
- **Docker** — Production deployment

### Planned
- SSO / SAML / OIDC authentication
- Prometheus metrics + Grafana dashboards
- Plugin system for custom providers
- Workflow templates
- Tool/function calling support
