# Roadmap

## Current Release: v0.1.0

The initial release focuses on a working local-first agent runtime with core routing, memory, and UI capabilities.

## v0.2.0 — Stability & Quality (Next)

**Target**: Improve reliability, test coverage, and developer experience.

- [ ] Reach 80%+ test coverage across all modules
- [ ] Add end-to-end integration tests for major workflows
- [ ] Implement proper error handling and retry logic in all providers
- [ ] Add structured logging with configurable levels
- [ ] Improve cold-start performance for local models
- [ ] Add health check and readiness probe endpoints

## v0.3.0 — Dashboard Experience

**Target**: Polish the web UI and add real-time features.

- [ ] Real-time model response streaming with animated UI
- [ ] Conversation branching and comparison
- [ ] Token usage and cost estimation dashboard
- [ ] Model performance benchmarks (latency, quality)
- [ ] Keyboard shortcuts and power-user features
- [ ] Mobile-responsive layout

## v0.4.0 — Advanced Routing

**Target**: Smarter task routing with user feedback integration.

- [ ] User feedback loop (thumbs up/down on responses)
- [ ] Automatic model selection based on historical success
- [ ] Prompt templates and presets
- [ ] Multi-turn conversation routing
- [ ] Custom routing rules (YAML configuration)

## v0.5.0 — Collaboration & Sharing

**Target**: Multi-user support and workspace sharing.

- [ ] User authentication and session management
- [ ] Shared workspaces and conversation export
- [ ] API key management UI
- [ ] Rate limiting and usage quotas
- [ ] Audit log viewer in dashboard

## v1.0.0 — Production Ready

**Target**: Stable, documented, and deployable.

- [ ] Helm chart for Kubernetes deployment
- [ ] Prometheus metrics and Grafana dashboards
- [ ] Database migration system
- [ ] Plugin system for custom providers
- [ ] Official Python package on PyPI
- [ ] Comprehensive security audit

## Future Ideas

- [ ] Voice interface (speech-to-text + TTS)
- [ ] Tool/function calling support
- [ ] RAG pipeline with document upload
- [ ] Multi-modal models (vision, audio)
- [ ] Local fine-tuning interface
- [ ] CI/CD integration (run tasks as GitHub Actions)

---

*This roadmap is aspirational and subject to change based on community feedback and contributor availability.*
