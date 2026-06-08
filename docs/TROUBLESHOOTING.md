# Troubleshooting Guide

## Table of Contents

- [Installation Issues](#installation-issues)
- [Backend Issues](#backend-issues)
- [Frontend Issues](#frontend-issues)
- [Model Routing Issues](#model-routing-issues)
- [Performance Issues](#performance-issues)
- [Docker Issues](#docker-issues)

## Installation Issues

### `ModuleNotFoundError: No module named 'nexus_r'`

**Cause**: Package not installed in editable mode.

**Fix**:
```bash
cd nexus-r
pip install -e ".[dev]"
```

### `npm install` fails with EACCES

**Cause**: npm permissions issue.

**Fix**:
```bash
# Use npx (recommended)
cd nexus-r/frontend
npx npm-ci

# Or fix permissions
sudo chown -R $(whoami) ~/.npm
```

### uv not found

**Fix**:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# Or: pip install uv
```

## Backend Issues

### `Address already in use` (port 8000)

**Fix**:
```bash
# Find and kill process
lsof -ti:8000 | xargs kill -9
# Or use different port
uvicorn modules.web_ui.src.app:app --port 8001
```

### Database locked errors

**Cause**: Multiple processes accessing SQLite simultaneously.

**Fix**:
```bash
# Ensure only one backend instance is running
# Use ChromaDB service for vector operations
make docker-up  # Uses isolated database volumes
```

### Model download stuck at 100%

**Cause**: Incomplete download or checksum mismatch.

**Fix**:
```bash
# Clear model cache
rm -rf ~/.nexus/models/
# Restart and retry download
```

## Frontend Issues

### Blank page after build

**Cause**: API URL mismatch or CORS issue.

**Fix**:
1. Check `WS_URL` in `frontend/src/api/client.ts`
2. Ensure backend is running on expected port
3. Check browser console for CORS errors

### Hot reload not working

**Fix**:
```bash
# Vite HMR requires WebSocket
cd nexus-r/frontend
npm run dev -- --host
```

## Model Routing Issues

### "No model available" error

**Cause**: No providers configured or models not downloaded.

**Fix**:
1. Go to Settings > Providers
2. Add at least one API key (or configure local Ollama)
3. Go to Settings > Models and download/select a model

### OpenRouter returns 404

**Cause**: Model name mismatch or invalid API key.

**Fix**:
```bash
# Verify API key
echo $NEXUS_BYOK_API_KEY
# Check available models at https://openrouter.ai/docs#models
```

### Local model not responding

**Fix**:
```bash
# Verify Ollama is running
ollama list
# Pull the model
ollama pull llama3.1:8b
```

## Performance Issues

### High memory usage

**Mitigations**:
- Use smaller models for simple tasks (auto-routing handles this)
- Reduce `context_window` in settings
- Enable memory compression in Advanced settings

### Slow first response

**Cause**: Cold-start model loading.

**Fix**:
- Use `_hot_reload_car()` to keep models warm
- Configure eager loading in settings

## Docker Issues

### Containers fail to start

```bash
# Check logs
docker compose logs backend
docker compose logs frontend

# Rebuild
docker compose down
docker compose build --no-cache
docker compose up -d
```

### Permission denied on volumes

```bash
# Fix volume permissions
sudo chown -R 1000:1000 ./data
# Or use Docker volumes instead of bind mounts
```

## Still Stuck?

1. Check [GitHub Discussions](https://github.com/gaurav-3821/NEXUS-R/discussions)
2. Open an issue with:
   - Your OS and version
   - Python/Node versions
   - Full error traceback
   - Steps to reproduce
