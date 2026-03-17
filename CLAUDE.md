# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Supply chain risk intelligence platform for semiconductor/electronics manufacturing. React dashboard frontend with a FastAPI + IBM Watson Orchestrate ADK backend for AI agent orchestration. All data is stored in a SQLite database (`data/mineralwatch.db`).

## Commands

### Frontend (`/Frontend`)

```bash
npm run dev        # Start Vite dev server with HMR (localhost:5173)
npm run build      # TypeScript check + production build
npm run lint       # ESLint
npm run preview    # Preview production build
```

### Backend (`/backend`)

```bash
pip install -r requirements.txt
uvicorn main:app --reload    # Run from /backend directory
```

### Tests

```bash
cd backend && python test_tools.py    # ADK tool smoke tests (mocks IBM SDK)
```

### Database Migration

```bash
cd backend && python migrate_to_db.py    # Rebuild mineralwatch.db from Excel sources
```

Environment variables required in root `.env`: `IBM_API_KEY`, `ORCHESTRATE_APIKEY`, `ORCHESTRATE_IAM_APIKEY`, `ORCHESTRATE_URL`, `ORCHESTRATE_AUTH_TYPE`.

## Architecture

### Frontend (React 19 + TypeScript + Vite + TailwindCSS v4)

- Single-page dashboard at `/` with a 12-column, 6-row grid layout
- Uses `react-globe.gl` + Three.js for 3D supply route visualization
- UI built with shadcn/ui (Radix primitives), Framer Motion for animations
- Path alias: `@` → `./src` (configured in vite.config.ts and tsconfig)
- Dark theme with IBM Plex fonts and risk-level color coding (red/amber/green)
- Data fetching via Axios + TanStack React Query against the FastAPI backend
- AgentWorkflow timeline and ScenariosPanel still use hardcoded simulated data from `src/data/simulatedData.ts`

**Dashboard Panels** (composed in `src/pages/Index.tsx`):
- **CompanySelector** — dropdown to pick a company for analysis
- **MetricsPanel** — risk score, trade concentration, corporate exposure, substitutability
- **GlobeView** — 3D globe with supply arcs colored by risk level
- **AgentWorkflow** — agent execution timeline (simulated data, not yet wired to real agents)
- **ScenariosPanel** — disruption scenario cards with sparklines (simulated data)
- **RiskTable** — trade flow table with concentration bars

### Backend (FastAPI + IBM Watson Orchestrate)

**`main.py`** — FastAPI app with CORS (allows `localhost:5173`). Endpoints:
- `GET /` — health check message
- `GET /health` — status ok
- `GET /companies` — list all companies in the DB
- `GET /analyze/{company}` — full risk analysis (trade + corporate + substitutability scores)
- `GET /api/minerals/list` — list all tracked minerals
- `GET /api/company/minerals/{company}` — minerals for a specific company
- `GET /api/mineral/risk/{mineral}` — trade concentration & supply risk for a mineral
- `GET /api/company/summary/{company}` — company name + risk summary snippet

**`analytics.py`** — risk analysis engine querying `mineralwatch.db`. Computes composite risk score using three weighted components:
- Trade Risk (40%): average HHI normalized to 0–100
- Corporate Risk (35%): mineral exposure breadth
- Substitutability Risk (25%): from USGS supply risk ratings

### ADK Agents (`backend/adk-project/`)

Three agents using `watsonx/ibm/granite-3-8b-instruct`:

| Agent | Style | Tools | Purpose |
|-------|-------|-------|---------|
| `trade_intel_agent` | ReAct | `query_import_volumes`, `compute_herfindahl`, `get_mineral_profile` | Trade flow analysis & supply concentration |
| `corporate_exposure_agent` | ReAct | `search_edgar_10k`, `extract_mineral_dependencies`, `summarize_risk_section` | SEC filing analysis & corporate risk |
| `risk_orchestrator` | Plan-Act | `compute_composite_risk`, `simulate_disruption`, `generate_mitigation_brief` | Coordinates sub-agents, computes final scores |

### ADK Tools (`backend/adk-project/tools/`)

All data-pulling tools query `mineralwatch.db` exclusively — no CSV or Excel reads at runtime.

| Tool | Source Table(s) | Purpose |
|------|----------------|---------|
| `query_import_volumes` | `trade_data` | Import volumes by mineral & country |
| `compute_herfindahl` | (pure computation) | HHI concentration index from trade flows |
| `get_mineral_profile` | `usgs_minerals`, `edgar_summary`, `edgar_blind_spot_analysis` | USGS mineral data + EDGAR enrichment |
| `extract_mineral_dependencies` | `edgar_mineral_company_matrix`, `edgar_filing_details`, `usgs_minerals` | Company mineral exposures with severity |
| `summarize_risk_section` | `edgar_filing_details`, `edgar_blind_spot_analysis`, `edgar_summary` | Company risk summary with exposure score |
| `compute_composite_risk` | `usgs_minerals` | Weighted composite score (trade 40%, corporate 35%, substitutability 25%) |
| `search_edgar_10k` | (live SEC EDGAR API) | Real-time filing search |
| `simulate_disruption` | (pure computation) | Disruption scenario modeling |
| `generate_mitigation_brief` | (stub) | Mitigation recommendations — awaiting Granite LLM |

Shared helpers in `_db.py`: `get_db_conn()`, `strip_mineral_qualifier()` (handles matrix names like `"HAFNIUM (see ZIRCONIUM)"`), `USGS_COL`, `DEFAULT_RISK_SCORE`.

### Database (`data/mineralwatch.db`)

SQLite database (~3 MB) with 8 tables, migrated from Excel via `backend/migrate_to_db.py`:

| Table | Source | Key Columns |
|-------|--------|-------------|
| `usgs_minerals` | USGS spreadsheet | Fab Stage, Commodity Name, Supply Risk, Top Producer, HTS Code |
| `trade_data` | USITC data | Year, Mineral, Country, Customs Value (USD) |
| `edgar_filing_details` | EDGAR scan | Mineral, Company, CIK, Form, Snippet |
| `edgar_summary` | EDGAR scan | Mineral, EDGAR Hits, Unique Companies, Risk Alignment |
| `edgar_mineral_company_matrix` | EDGAR scan | Company × 45 mineral columns (presence/frequency) |
| `edgar_blind_spot_analysis` | EDGAR scan | Mineral, Supply Risk, Assessment, Action |
| `edgar_company_filings` | EDGAR scan | Company, CIK, Form, Filed, URL |
| `edgar_scan_metadata` | EDGAR scan | Scan metadata |

Indexed columns: `trade_data(Mineral, Country)`, `edgar_filing_details(Company, Mineral)`.

**Note:** Some column names contain literal newlines (e.g., `"USGS Commodity Name\n(exact CSV name)"`). The shared `USGS_COL` constant in `_db.py` handles this. Matrix mineral columns use UPPERCASE with qualifiers (e.g., `"DIAMOND (INDUSTRIAL)*"`) — use `strip_mineral_qualifier()` before USGS lookups.

Source Excel files in `data/`: `Semiconductor_Minerals_USGS_Map_With_HTS.xlsx`, `edgar_mineral_results.xlsx`, `usitc_clean.xlsx`.

## Package Management

- Frontend: npm
- Backend: pip (not uv)
