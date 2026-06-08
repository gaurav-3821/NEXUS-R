# Social Preview Specification

GitHub uses Open Graph and Twitter Card metadata when links to the repository
are shared on social media. Since NEXUS-R uses the default repository metadata,
we recommend configuring a custom social preview image.

## Required Image

| Property | Value |
|----------|-------|
| Path | `docs/assets/social-preview.png` (or any path in the repo) |
| Dimensions | **1280×640 pixels** (exact, 2:1 ratio) |
| Format | PNG |
| Max Size | 1MB |
| DPI | 72 |

## How to Set

1. Go to **Settings > General > Social preview**
2. Click **Edit**
3. Upload `docs/assets/social-preview.png`
4. Click **Save**

## Design Guidelines

### Include
- NEXUS-R logo/brandmark (left or center)
- Tagline: "Local-first agent runtime" (below logo)
- Repository name: `gaurav-3821/NEXUS-R` (bottom right)
- Clean background (dark mode preferred, #1e1e2e or similar)

### Avoid
- Cluttered layouts
- Small text (will be illegible when shared)
- Platform-specific branding (Twitter, LinkedIn, etc.)
- Screenshots of the app (too detailed for small cards)

## Preview Tools

Use these tools to verify how your social preview appears:

- [Twitter Card Validator](https://cards-dev.twitter.com/validator)
- [LinkedIn Post Inspector](https://www.linkedin.com/post-inspector/)
- [Open Graph Debugger](https://opengraph.dev/)

## Reference

GitHub automatically caches the social preview image. Updates may take
up to 24 hours to propagate across all sharing platforms.
