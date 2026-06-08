# Frequently Asked Questions

## General

### What is NEXUS-R?

NEXUS-R is a local-first agent runtime that lets you execute AI-assisted workspace tasks with full control over where your data goes. It routes tasks between local models (Ollama) and cloud providers based on complexity, cost, and your privacy preferences.

### Is NEXUS-R free?

Yes. NEXUS-R itself is open-source (MIT license). You bring your own API keys for cloud providers. Local models via Ollama are free.

### What platforms are supported?

- macOS 14+ (Apple Silicon and Intel)
- Linux (Ubuntu 22.04+, Fedora 39+, Arch)
- Windows 11+ (via WSL2 recommended)

## Features

### Which AI providers are supported?

| Provider | Type | Status |
|----------|------|--------|
| Ollama | Local | Full support |
| OpenAI | Cloud | Full support |
| Anthropic (Claude) | Cloud | Full support |
| OpenRouter | Cloud | Full support |
| Groq | Cloud | Full support |
| Google (Gemini) | Cloud | Full support |
| Cohere | Cloud | Full support |
| Mistral | Cloud | Full support |
| Together AI | Cloud | Full support |
| Azure OpenAI | Cloud | Coming soon |

### Can I use NEXUS-R without internet?

Yes, if you configure local models via Ollama. Cloud providers require internet access.

### How does the routing work?

The Cognition Router analyzes your task's complexity and routes it:
- **Simple tasks** (T1-T2) -> Local models (free, private)
- **Complex tasks** (T3-T5) -> Cloud providers (capable, metered)

You can override routing per-task or set a default profile.

### Is my data sent to cloud providers?

Only when routing decides a cloud model is needed. You can:
- Force local-only mode
- Set a "local preference" profile
- Review the routing rationale before execution

## Development

### How do I add a new model provider?

1. Add provider configuration to `nexus_r/config.py`
2. Implement adapter in `modules/cognition_router/src/`
3. Add unit tests in `tests/unit/`
4. Update the frontend provider list

See the full guide in [CONTRIBUTING.md](CONTRIBUTING.md).

### Can I use NEXUS-R as a library?

Not yet -- the runtime is designed as an application. Library packaging is on the [roadmap](ROADMAP.md).

## Troubleshooting

### Where are logs stored?

- Backend: `~/.nexus/logs/`
- Frontend: Browser DevTools console
- Docker: `docker compose logs`

### How do I reset all data?

```bash
# WARNING: This deletes all conversations, memory, and settings
rm -rf ~/.nexus/
# Or via Docker:
docker compose down -v
```

### Where do I report bugs?

[GitHub Issues](https://github.com/gaurav-3821/NEXUS-R/issues) -- check existing issues first.
