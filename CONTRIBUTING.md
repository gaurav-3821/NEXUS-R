# Contributing to NEXUS-R

Thank you for your interest in contributing to NEXUS-R! This document provides
guidelines and workflows for effective collaboration.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Code Standards](#code-standards)
- [Testing Requirements](#testing-requirements)
- [Pull Request Process](#pull-request-process)
- [Release Process](#release-process)

## Code of Conduct

This project adheres to the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md).
By participating, you are expected to uphold this code.

## Getting Started

### Prerequisites

- Python 3.11+ and Node.js 22+
- Git with signed commits recommended
- Docker (optional, for integration testing)

### Setup

```bash
git clone https://github.com/gaurav-3821/NEXUS-R.git
cd NEXUS-R
make setup
```

This installs all dependencies, configures pre-commit hooks, and verifies your environment.

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
```

Branch naming conventions:
- `feature/description` -- New features
- `fix/description` -- Bug fixes
- `docs/description` -- Documentation changes
- `refactor/description` -- Code refactoring
- `test/description` -- Test additions/improvements

### 2. Make Changes

- Follow [code standards](#code-standards)
- Add/update tests as needed
- Update documentation if behavior changes

### 3. Verify

```bash
make lint        # Must pass
make typecheck   # Must pass
make test        # All tests must pass (backend + frontend)
make security    # No new vulnerabilities
```

### 4. Commit

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add OpenRouter reasoning support
fix: correct tier escalation edge case
docs: update API endpoint documentation
test: add property-based tests for routing
refactor: extract route handlers from app.py
chore: update dependency versions
```

### 5. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Then open a Pull Request using the provided template.

## Code Standards

### Python

- **Formatter**: Ruff (replaces black + isort)
- **Linter**: Ruff
- **Type Checker**: MyPy (strict mode)
- **Line Length**: 100 characters
- **Docstrings**: Google style
- **Type Hints**: Required on all public functions

### TypeScript / Frontend

- **Linter**: ESLint with TypeScript plugin
- **Formatter**: Prettier
- **Type Checker**: TypeScript strict mode
- **Line Length**: 100 characters
- **Component Style**: Functional components with hooks

### Code Review Checklist

Before requesting review, ensure:

- [ ] Code follows style guidelines (lint passes)
- [ ] All types are correct (typecheck passes)
- [ ] Tests added/updated and passing
- [ ] No new security vulnerabilities
- [ ] Documentation updated if needed
- [ ] Commit messages follow conventional format
- [ ] PR description is complete

## Testing Requirements

### Coverage Thresholds

| Suite | Minimum Coverage |
|-------|-----------------|
| Backend unit tests | 70% |
| Backend integration tests | 60% |
| Frontend unit tests | 60% |
| Security tests | Must pass |

### Running Tests

```bash
# Backend
pytest tests/unit -v                    # Unit tests
pytest tests/integration -v             # Integration tests
pytest tests/security -v                # Security tests
pytest tests/ -v --cov --cov-report=html # With coverage

# Frontend
npm run test:unit                       # Unit tests
npm run test:unit -- --coverage         # With coverage
npm run test:e2e                        # E2E tests (requires dev server)
```

## Pull Request Process

1. **Open PR** using the provided template
2. **CI must pass** -- all GitHub Actions checks green
3. **Code review** -- at least one maintainer approval
4. **Address feedback** -- iterate on review comments
5. **Squash merge** -- maintain clean commit history

## Release Process

Releases follow [Semantic Versioning](https://semver.org/):

1. Update `CHANGELOG.md`
2. Bump version in `pyproject.toml`
3. Create Git tag: `git tag v0.2.0`
4. Push tag: `git push origin v0.2.0`
5. GitHub Actions auto-publishes release

## Questions?

- Open a [Discussion](https://github.com/gaurav-3821/NEXUS-R/discussions)
- Check [FAQ](docs/FAQ.md)
- Read [Troubleshooting](docs/TROUBLESHOOTING.md)
