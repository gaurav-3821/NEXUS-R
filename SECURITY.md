# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

To report a security vulnerability, please email **gauravtayde3821@gmail.com**.

Do not create public GitHub issues for security vulnerabilities.

### What to include

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if known)

### Response Timeline

- **24 hours**: Acknowledgment of receipt
- **7 days**: Initial assessment and mitigation plan
- **30 days**: Fix released (depending on severity)

## Security Best Practices

### API Keys

- Store API keys in environment variables, never in code
- Use `.env` files in development (already in `.gitignore`)
- Rotate keys regularly

### Local Models

- Downloaded models are cached in `~/.nexus/models/`
- Only pull models from trusted sources (Ollama library, Hugging Face)

### Network

- The backend binds to `127.0.0.1` by default (localhost only)
- For production, use a reverse proxy (see `nginx.conf`)
- WebSocket connections are unencrypted in dev; use HTTPS in production

### Data

- Conversation history is stored locally in SQLite
- Vector embeddings are stored locally in ChromaDB
- No telemetry or usage data is sent externally
