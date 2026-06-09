# Image Placement Guide

This document specifies where to place images referenced in NEXUS-R documentation.

## Directory Structure

```
docs/assets/
  ss-chat.png             # Chat interface
  ss-chat-model.png       # Model picker within chat
  ss-models.png           # Models settings tab
  ss-model-discovery.png  # Model discovery center
  ss-appearance.png       # Appearance settings
  ss-api-keys.png         # API key configuration
  ss-about.png            # About page
  ss-agent-tools.png      # Agent tool configuration
  ss-memory.png           # Memory settings tab
  nexus-r-banner.png      # README header banner (optional)
```

## Image Specifications

| Image | Format | Max Size | DPI |
|-------|--------|----------|-----|
| Screenshots | PNG | 500KB | 72 |
| Banner | PNG | 200KB | 72 |

## Naming Convention

- Lowercase with hyphens: `screenshot-settings.png`
- Descriptive: `quickstart-wizard.gif` not `demo1.gif`
- No spaces or special characters

## How to Capture

### Screenshots
1. Open the dashboard in a clean browser window
2. Use browser DevTools to set viewport to 1440×900
3. Capture full-page where needed

### Architecture Diagram
- Use draw.io or Mermaid
- Export as PNG at 2x resolution
- Place in `docs/assets/`

## Updating

When you add a new image:
1. Place it in `docs/assets/`
2. Reference it in `README.md` using relative path: `docs/assets/your-image.png`
3. Update this document if adding new image types
