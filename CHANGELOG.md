# Changelog

All notable changes to NEXUS-R are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Health check and readiness probe endpoints
- Docker Compose stack with ChromaDB
- Pre-commit hooks (ruff, mypy, bandit)
- GitHub Actions CI/CD pipeline
- Property-based tests for routing invariants
- Frontend unit test suite (Vitest + React Testing Library)
- End-to-end test suite (Playwright)
- Comprehensive documentation (FAQ, Troubleshooting, Contributing)

### Changed
- Migrated to Ruff for Python linting and formatting
- Added MyPy strict mode for static type checking
- Updated frontend package.json with complete test scripts
- Improved README with badges, screenshots, and quick start

### Fixed
- Model download progress stuck at 100%
- OpenRouter routing 404 errors for missing models
- Dark mode toggle initialization on app mount
- API key input field focus and validation

## [0.1.0] - 2026-06-08

### Added
- Initial release of NEXUS-R agent runtime
- CLI interface with `nexus run`, `nexus dashboard start`
- Web dashboard with React 19 + TypeScript
- Multi-provider model routing (10+ providers)
- Permission tier system (T1-T5)
- Memory engine with ChromaDB vector storage
- Real-time telemetry via WebSocket
- Cost tracking dashboard
- Theme system (light/dark + accent colors)
- Model management UI with download progress
- Conversation persistence and history
- 20+ unit tests across all modules
- Architecture documentation and module specifications

[Unreleased]: https://github.com/gaurav-3821/NEXUS-R/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/gaurav-3821/NEXUS-R/releases/tag/v0.1.0
