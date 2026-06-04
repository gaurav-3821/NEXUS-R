# NEXUS-R Frontend

This directory contains the current dashboard source for NEXUS-R.

## Stack

- React 19
- TypeScript
- Vite 8
- Zustand
- Tailwind CSS
- Framer Motion

## Key Paths

- `src/App.tsx`: top-level application shell
- `src/components/`: chat, settings, layout, sidebar, and UI building blocks
- `src/store/`: Zustand stores for app, models, providers, memory, workflow,
  and dashboard state
- `src/api/`: client calls for chat, models, providers, workflow, and dashboard
- `public/`: static icons and favicon

## Commands

```bash
npm install
npm run dev
npm run build
npm run lint
```

## Build Output

The backend serves built assets from:

`../modules/web_ui/src/static/`

When frontend behavior changes, keep the source and served build output aligned.
