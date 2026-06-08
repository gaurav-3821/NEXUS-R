.PHONY: help setup install backend-install frontend-install test backend-test frontend-test lint backend-lint frontend-lint format backend-format frontend-format typecheck backend-typecheck frontend-typecheck security build clean run docs coverage docker-build docker-up docker-down

help:
	@echo "NEXUS-R Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make setup               Full setup (backend + frontend)"
	@echo "  make install             Install all dependencies"
	@echo ""
	@echo "Development:"
	@echo "  make run                 Run backend + frontend dev servers"
	@echo "  make run-backend         Run FastAPI backend only"
	@echo "  make run-frontend        Run Vite frontend dev server only"
	@echo ""
	@echo "Testing:"
	@echo "  make test                Run all tests"
	@echo "  make backend-test        Run Python tests with coverage"
	@echo "  make frontend-test       Run frontend tests"
	@echo "  make coverage            Generate coverage report"
	@echo ""
	@echo "Quality:"
	@echo "  make lint                Lint all code"
	@echo "  make format              Format all code"
	@echo "  make typecheck           Type-check all code"
	@echo "  make security            Run security scans"
	@echo ""
	@echo "Build & Deploy:"
	@echo "  make build               Build frontend for production"
	@echo "  make docker-build        Build Docker images"
	@echo "  make docker-up           Start Docker compose stack"
	@echo "  make docker-down         Stop Docker compose stack"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean               Clean generated files"
	@echo "  make docs                Build documentation"

setup: install
	@echo "Setup complete. Run 'make run' to start development."

install: backend-install frontend-install

backend-install:
	cd nexus-r && uv pip install -e ".[dev]"
	cd nexus-r && uv pip install ruff mypy pytest-cov bandit

frontend-install:
	cd nexus-r/frontend && npm ci

run:
	@echo "Starting backend and frontend..."
	@(trap 'kill %1 %2' EXIT; \
		make run-backend & \
		make run-frontend & \
		wait)

run-backend:
	cd nexus-r && python -m uvicorn modules.web_ui.src.app:app --reload --host 0.0.0.0 --port 8000

run-frontend:
	cd nexus-r/frontend && npm run dev

test: backend-test frontend-test

backend-test:
	cd nexus-r && pytest tests/ -v --cov=. --cov-report=term-missing

backend-test-unit:
	cd nexus-r && pytest tests/unit -v

backend-test-integration:
	cd nexus-r && pytest tests/integration -v

backend-test-security:
	cd nexus-r && pytest tests/security -v

backend-test-stress:
	cd nexus-r && pytest tests/stress -v

frontend-test:
	cd nexus-r/frontend && npm run test:unit

frontend-test-e2e:
	cd nexus-r/frontend && npm run test:e2e

coverage:
	cd nexus-r && pytest tests/ -v --cov=. --cov-report=html --cov-report=xml
	@echo "Coverage report: nexus-r/htmlcov/index.html"

lint: backend-lint frontend-lint

backend-lint:
	cd nexus-r && ruff check .
	cd nexus-r && ruff format --check .

frontend-lint:
	cd nexus-r/frontend && npm run lint

format: backend-format frontend-format

backend-format:
	cd nexus-r && ruff check . --fix
	cd nexus-r && ruff format .

frontend-format:
	cd nexus-r/frontend && npm run format 2>/dev/null || npx prettier --write "src/**/*.{ts,tsx,css}"

typecheck: backend-typecheck frontend-typecheck

backend-typecheck:
	cd nexus-r && mypy foundation/ modules/ --ignore-missing-imports

frontend-typecheck:
	cd nexus-r/frontend && npx tsc --noEmit

security: backend-security frontend-security

backend-security:
	cd nexus-r && bandit -r foundation/ modules/ -f txt || true

frontend-security:
	cd nexus-r/frontend && npm audit --audit-level=moderate || true

build: frontend-build

frontend-build:
	cd nexus-r/frontend && npm run build

docker-build:
	docker compose -f docker-compose.yml build

docker-up:
	docker compose -f docker-compose.yml up -d

docker-down:
	docker compose -f docker-compose.yml down

docs:
	cd docs && mkdocs serve

clean:
	find nexus-r -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find nexus-r -type f -name '*.pyc' -delete 2>/dev/null || true
	find nexus-r -type d -name '*.egg-info' -exec rm -rf {} + 2>/dev/null || true
	find nexus-r -type d -name '.pytest_cache' -exec rm -rf {} + 2>/dev/null || true
	find nexus-r -type d -name '.mypy_cache' -exec rm -rf {} + 2>/dev/null || true
	find nexus-r -type d -name 'htmlcov' -exec rm -rf {} + 2>/dev/null || true
	rm -f nexus-r/.coverage nexus-r/coverage.xml
	rm -rf nexus-r/frontend/dist
	rm -rf nexus-r/frontend/node_modules/.vitest
	@echo "Cleanup complete"
