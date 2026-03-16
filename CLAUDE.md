# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Supply chain risk intelligence platform for semiconductor/electronics manufacturing. React dashboard frontend with a FastAPI + IBM Watson Orchestrate ADK backend for AI agent orchestration.

## Commands

### Frontend (`/Frontend`)

```bash
npm run dev        # Start Vite dev server with HMR
npm run build      # TypeScript check + production build
npm run lint       # ESLint
npm run preview    # Preview production build
```

### Backend (`/backend`)

```bash
pip install -r requirements.txt
uvicorn main:app --reload    # Run from /backend directory
```

Environment variables required in root `.env`: `IBM_API_KEY`, `ORCHESTRATE_APIKEY`, `ORCHESTRATE_IAM_APIKEY`, `ORCHESTRATE_URL`, `ORCHESTRATE_AUTH_TYPE`.

## Architecture

**Frontend** (React 19 + TypeScript + Vite + TailwindCSS v4):
- Single-page dashboard at `/` with a 12-column grid layout
- Uses `react-globe.gl` + Three.js for 3D supply route visualization
- UI built with shadcn/ui (Radix primitives), Framer Motion for animations
- Path alias: `@` → `./src` (configured in vite.config.ts and tsconfig)
- All data currently comes from hardcoded simulated data in `src/data/simulatedData.ts` — no live API integration yet
- Dark theme with IBM Plex fonts and risk-level color coding (red/amber/green)

**Backend** (FastAPI + IBM Watson Orchestrate):
- `main.py` — FastAPI app with `/` and `/health` endpoints (stub)
- `adk-project/` — Watson ADK agent project structure with `agents/`, `tools/`, `flows/`, `knowledge/` directories (mostly empty, hello-world agent only)

**Dashboard Panels**: MetricsPanel, GlobeView, AgentWorkflow, ScenariosPanel, RiskTable — all composed in `src/pages/Index.tsx`.

## Package Management

- Frontend: npm
- Backend: pip (not uv)
