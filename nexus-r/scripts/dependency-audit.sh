#!/usr/bin/env bash
set -euo pipefail

echo "=== Python Dependency Audit ==="
if command -v safety &> /dev/null; then
    safety check --full-report || true
else
    echo "safety not installed, skipping Python dep audit"
fi

echo ""
echo "=== Python Package Vulnerabilities (pip-audit) ==="
if command -v pip-audit &> /dev/null; then
    pip-audit --desc || true
else
    echo "pip-audit not installed, skipping"
fi

echo ""
echo "=== npm Dependency Audit ==="
cd nexus-r/frontend
npm audit --audit-level=moderate || true

echo ""
echo "=== Outdated Packages ==="
echo "--- Python ---"
cd ../..
cd nexus-r
pip list --outdated 2>/dev/null || true
echo ""
echo "--- npm ---"
cd frontend
npm outdated || true

echo ""
echo "=== Audit Complete ==="
