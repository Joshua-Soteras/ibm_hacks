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
cd backend
source .venv/bin/activate              # Always activate the venv first
pip install -r requirements.txt
uvicorn main:app --reload              # Run from /backend directory (localhost:8000)
```

### Tests

```bash
cd backend && .venv/bin/python test_tools.py    # ADK tool smoke tests (mocks IBM SDK)
```

### Database Migration

```bash
cd backend && .venv/bin/python migrate_to_db.py    # Rebuild mineralwatch.db from Excel sources
```

Environment variables required in root `.env`: `IBM_API_KEY`, `ORCHESTRATE_APIKEY`, `ORCHESTRATE_IAM_APIKEY`, `ORCHESTRATE_URL`, `ORCHESTRATE_AUTH_TYPE`.

Optional: `BACKEND_API_URL` — public URL of the FastAPI backend (e.g. ngrok tunnel). Used by ADK tools in cloud deployment to call back to the backend instead of querying local SQLite. Not needed for local dev.

## Architecture

### Frontend (React 19 + TypeScript + Vite + TailwindCSS v4)

- Single-page dashboard at `/` with a 12-column, 6-row grid layout
- Uses `react-globe.gl` + Three.js for 3D supply route visualization
- UI built with shadcn/ui (Radix primitives), Framer Motion for animations
- Path alias: `@` → `./src` (configured in vite.config.ts and tsconfig)
- Dark theme with IBM Plex fonts and risk-level color coding (red/amber/green)
- Data fetching via Axios + TanStack React Query against the FastAPI backend
- SSE streaming via `useAnalysisStream` hook for real-time agent workflow updates
- All 6 dashboard panels are now wired to real backend data (no hardcoded mock data)

**Dashboard Panels** (composed in `src/pages/Index.tsx`):
- **CompanySelector** — dropdown to pick a company for analysis
- **MetricsPanel** — risk score, trade concentration, corporate exposure, substitutability; shows disrupted scores + delta during simulation
- **GlobeView** — 3D globe with supply arcs colored by risk level; supports disrupted/stressed/active arc states during simulation
- **AgentWorkflow** — real-time agent execution timeline streamed via SSE from `/api/analyze-stream/{company}`; expandable full agent output on steps with truncated content (animated expand/collapse)
- **ScenariosPanel** — dynamic disruption scenario cards generated from trade concentration data; click-to-simulate with reset; custom free-text scenario input that invokes the cloud agent
- **RiskTable** — sortable trade flow table with concentration bars (click column headers to sort)

**Key Frontend Files:**
- `src/hooks/useAnalysisStream.ts` — SSE hook using `EventSource` API, manages 4-step agent workflow state; `AgentStepData` includes optional `full_output` for untruncated agent text
- `src/hooks/useCustomScenarioStream.ts` — SSE hook for free-text custom scenario analysis via `/api/custom-scenario-stream/{company}`; stores `full_output` from SSE events
- `src/lib/api.ts` — Axios API client with TypeScript interfaces (`ScenarioCard`, `SimulationResult`)
- `src/data/countryCoords.json` — ~130 country centroid coordinates for globe arc rendering
- `src/data/simulatedData.ts` — legacy mock data (no longer imported by any component)

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
- `GET /api/company/scenarios/{company}` — dynamic disruption scenarios based on trade concentration (minerals with >30% single-country share)
- `POST /api/simulate` — accepts `{company, country, mineral, disruption_pct?}`, returns disrupted risk scores with flow statuses
- `GET /api/mineral/trade/{mineral}?year=` — import volumes by country for a mineral (ADK tool callback)
- `GET /api/mineral/profile/{mineral}` — structured USGS/EDGAR mineral profile (ADK tool callback)
- `GET /api/company/dependencies/{company}` — mineral dependencies with severity (ADK tool callback)
- `GET /api/risk-summary?company=&mineral=` — risk summary, company-centric or mineral-centric (ADK tool callback)
- `GET /api/edgar/cik/{company}` — CIK lookup from EDGAR data (ADK tool callback)
- `GET /api/analyze-stream/{company}` — SSE endpoint streaming staged analysis events (orchestrator_planning → trade_intel → corporate_exposure → orchestrator_scoring → complete)
- `GET /api/custom-scenario-stream/{company}?scenario=` — SSE endpoint for free-text custom scenario analysis via cloud agent
- `GET /api/agent-diagnostics` — debug endpoint: env var status, agent UUID resolution, callback reachability

**`analytics.py`** — risk analysis engine querying `mineralwatch.db`. Decomposed into staged helpers for SSE streaming:
- `_get_trade_data_for_company(company, conn, minerals)` — trade flows + HHI computation
- `_get_corporate_data_for_company(conn, minerals)` — USGS-based corporate + substitutability scores
- `analyze_company(company)` — full analysis (calls both helpers), same return shape as before
- `get_company_scenarios(company)` — generates up to 5 disruption scenarios from concentrated trade flows
- `simulate_company_disruption(company, country, mineral, disruption_pct)` — re-scores with a country/mineral removed, uplifts corporate by 15, marks flows as disrupted/stressed/active
- `get_mineral_trade_flows(mineral, year)` — import volumes grouped by country (ADK tool callback)
- `get_mineral_profile_data(mineral)` — structured mineral profile from USGS/EDGAR (ADK tool callback)
- `get_company_dependencies(company)` — mineral dependencies with severity from matrix + filing fallback (ADK tool callback)
- `get_risk_summary(company, mineral)` — company-centric or mineral-centric risk summary (ADK tool callback)
- `lookup_edgar_cik(company)` — CIK lookup from EDGAR data (ADK tool callback)

**`agent_client.py`** — IBM Watson Orchestrate RunClient integration for invoking the deployed `risk_orchestrator` agent. Uses IAM authentication, agent UUID resolution, and polling for run completion. Falls back to keyword-based extraction + local `simulate_company_disruption()` if the agent is unavailable. Powers both `/api/analyze-stream/{company}` (concurrent agent + local analytics) and `/api/custom-scenario-stream/{company}` (agent-only with simulation). Includes apology/refusal detection (`_is_agent_useful()`) — when the cloud LLM returns conversational refusals instead of tool outputs, the local analytics summary is preserved and the result includes `agent_enriched: false`. SSE events include `full_output` field with untruncated agent text when the response exceeds the display truncation threshold (300 chars for standard analysis, 600 chars for custom scenarios).

**`analytics.py`** includes `resolve_company_name()` which normalizes company names for callback endpoints. Handles LLM-reformulated names (e.g., "Amazon.com Inc" → "AMAZON COM INC") by stripping punctuation and doing case-insensitive matching against the DB.

Computes composite risk score using three weighted components:
- Trade Risk (40%): average HHI normalized to 0–100 via piecewise DOJ/FTC thresholds (0-1500→0-30, 1500-2500→30-60, 2500-5000→60-85, 5000-10000→85-100)
- Corporate Risk (35%): severity-weighted average of USGS supply risk scores per mineral
- Substitutability Risk (25%): from USGS supply risk ratings (LOW=20, MODERATE=50, HIGH=70, CRITICAL=90)

### ADK Agents (`backend/adk-project/`)

Three agents using `groq/openai/gpt-oss-120b` (Groq-served, 120B params, fast inference with native tool-calling):

| Agent | Style | Tools | Purpose |
|-------|-------|-------|---------|
| `trade_intel_agent` | ReAct | `query_import_volumes`, `compute_herfindahl`, `get_mineral_profile` | Trade flow analysis & supply concentration |
| `corporate_exposure_agent` | ReAct | `extract_mineral_dependencies`, `summarize_risk_section`, `search_edgar_10k` | SEC filing analysis & corporate risk (DB-first, live API as supplement) |
| `risk_orchestrator` | Plan-Act | `compute_composite_risk`, `simulate_disruption` | Coordinates sub-agents, computes final scores |

### ADK Tools (`backend/adk-project/tools/`)

Tools support dual-mode data access: local SQLite (default) or HTTP callbacks to the FastAPI backend when `BACKEND_API_URL` is set (cloud deployment). The switch is controlled by `_api.py:is_api_mode()` which resolves the URL from either an Orchestrate `key_value_creds` connection (`app_id: backend_api`) or the `BACKEND_API_URL` env var.

| Tool | Source Table(s) | Purpose |
|------|----------------|---------|
| `query_import_volumes` | `trade_data` | Import volumes by mineral & country |
| `compute_herfindahl` | (pure computation) | HHI concentration index from trade flows |
| `get_mineral_profile` | `usgs_minerals`, `edgar_summary`, `edgar_blind_spot_analysis` | USGS mineral data + EDGAR enrichment |
| `extract_mineral_dependencies` | `edgar_mineral_company_matrix`, `edgar_filing_details`, `usgs_minerals` | Company mineral exposures with severity (matrix for 40 companies, filing_details fallback for ~1,020) |
| `summarize_risk_section` | `edgar_filing_details`, `edgar_blind_spot_analysis`, `edgar_summary`, `usgs_minerals` | Company or mineral-centric risk summary with exposure score (optional `mineral_name` param for mineral-centric mode) |
| `compute_composite_risk` | `usgs_minerals` | Weighted composite score with piecewise HHI normalization (trade 40%, corporate 35%, substitutability 25%) |
| `search_edgar_10k` | (live SEC EDGAR API) + `edgar_company_filings` for CIK lookup | Real-time filing search (supplemental freshness check) |
| `simulate_disruption` | (pure computation) | Disruption scenario modeling |
| `generate_mitigation_brief` | (stub, not wired to any agent) | Mitigation recommendations — awaiting Granite LLM |

Shared helpers (local dev only — cloud tools inline these via try/except fallback):
- `_db.py`: `get_db_conn()` (raises `FileNotFoundError` with guidance when DB missing), `strip_mineral_qualifier()`, `USGS_COL`, `DEFAULT_RISK_SCORE`
- `_api.py`: `is_api_mode()`, `api_get()`, `BACKEND_CONNECTION` (credential declaration for `@tool()` decorators)

**Cloud compatibility:** Each tool file wraps `_api`/`_db` imports in `try/except (ImportError, ModuleNotFoundError)` with inlined fallback definitions. Watson Orchestrate imports tools as standalone files (no access to sibling modules), so the fallback provides `BACKEND_CONNECTION`, `is_api_mode()`, `api_get()`, constants, and a `get_db_conn()` stub that raises `RuntimeError`.

### Cloud Deployment (IBM Watson Orchestrate)

ADK tools are deployed to Watson Orchestrate cloud. Since the SQLite DB isn't available there, tools call back to the FastAPI backend via HTTP. Setup:

```bash
# 1. Create connection for backend URL
orchestrate connections add --app-id backend_api
orchestrate connections configure --app-id backend_api --env draft --kind key_value --type team
orchestrate connections configure --app-id backend_api --env live --kind key_value --type team
orchestrate connections set-credentials --app-id backend_api --env draft --entries "BACKEND_API_URL=https://your-backend-url"
orchestrate connections set-credentials --app-id backend_api --env live --entries "BACKEND_API_URL=https://your-backend-url"

# 2. Import tools with connection binding
for t in query_import_volumes get_mineral_profile extract_mineral_deps summarize_risk_section search_edgar_10k compute_composite_risk; do
  orchestrate tools import --file "tools/${t}.py" --kind python --app-id backend_api
done

# 3. Import and deploy agents
orchestrate agents import --file agents/trade_intel_agent.yaml
orchestrate agents import --file agents/corporate_exposure_agent.yaml
orchestrate agents import --file agents/risk_orchestrator.yaml
orchestrate agents deploy --name trade_intel_agent
orchestrate agents deploy --name corporate_exposure_agent
orchestrate agents deploy --name risk_orchestrator
```

For local dev with ngrok: set `BACKEND_API_URL` in `.env` and run ngrok on port 8000. The `_api.py` helper includes an `ngrok-skip-browser-warning` header to bypass the free-tier interstitial.

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
- Backend: pip (not uv), always use the `.venv` in `backend/.venv/`
