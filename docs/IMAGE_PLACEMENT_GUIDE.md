# Image Placement Guide

This document specifies where to place images referenced in NEXUS-R documentation.

## Directory Structure

```
docs/assets/
  nexus-r-banner.png          # 800×200, used in README header
  nexus-r-dashboard-preview.png  # ~1200×800, used in README Overview
  architecture-diagram.png    # ~1200×600, used in README Architecture
  quickstart-wizard.gif       # ~800×500, used in README First Run
  screenshot-chat.png         # ~1200×800, used in README Chat
  screenshot-models.png       # ~1200×800, used in README Models
  screenshot-settings.png     # ~1200×800, used in README Settings
```

## Image Specifications

| Image | Format | Max Width | Max Size | DPI |
|-------|--------|-----------|----------|-----|
| Banner | PNG | 800px | 200KB | 72 |
| Dashboard preview | PNG | 1200px | 500KB | 72 |
| Architecture diagram | PNG | 1200px | 500KB | 72 |
| Animated demo | GIF | 800px | 2MB | 72 |
| Screenshots | PNG | 1200px | 500KB | 72 |

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
