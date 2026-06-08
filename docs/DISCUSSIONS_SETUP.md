# Setting Up GitHub Discussions

This guide explains how to enable and configure GitHub Discussions for the NEXUS-R repository.

## Prerequisites

- Admin or maintainer access to the repository

## Enabling Discussions

1. Go to **Settings > General > Features**
2. Scroll to **Discussions**
3. Click **Set up discussions**
4. Choose a format (recommended: **Categories with issues**)
5. Click **Start discussion**

## Recommended Categories

| Category | Description | Format |
|----------|-------------|--------|
| 🎉 Announcements | Release notes and project updates | Announcement |
| 💡 Ideas | Feature suggestions and proposals | Open-ended |
| 🙏 Q&A | Help and troubleshooting | Q&A |
| 🗣 General | General discussion | Open-ended |
| 📖 Show and tell | Share what you built with NEXUS-R | Show and tell |

## Pinning

Pin these discussions for visibility:
1. **Welcome to NEXUS-R** -- introduction and quick links
2. **FAQ** -- link to the FAQ document
3. **Contributing Guide** -- link to CONTRIBUTING.md

## Linking from Issues

In `config.yml` (`.github/ISSUE_TEMPLATE/`), we already link to Discussions.
Make sure the URL matches your repository URL after Discussions is enabled.

## Moderation

- Enable **Require approval for all new discussion posts** in Settings > Moderation
- Assign maintainers as moderators
- Lock resolved Q&A threads after 30 days of inactivity
