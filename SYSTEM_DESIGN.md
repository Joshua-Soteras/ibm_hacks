# Roq — System Design Document

## Project Overview

Roq is a multi-agent AI application that assesses semiconductor companies' exposure to critical mineral supply chain disruptions. It combines U.S. government trade data, SEC corporate filings, and USGS mineral intelligence into a unified risk score, visualized on an interactive 3D globe.

**One-liner:** Multi-agent supply chain risk intelligence for critical semiconductor minerals — with scenario simulation for export disruption events.

**Hackathon track:** Semiconductor Manufacturing — specifically the "AI agent that monitors supply chain risks and recommends mitigation strategies" use case.

**IBM Stack:** watsonx Orchestrate ADK + Groq-served gpt-oss-120b (120B params, fast inference with native tool-calling)

---

## Problem Statement

Semiconductor manufacturers have no automated way to assess their compound exposure to mineral supply disruptions. A company might know it uses gallium, but not that 98% of US gallium imports originate from a single country, or that their own 10-K annual filing already flags this as a material risk. When an export ban drops, they are reactive instead of prepared.

The core insight: no single public data source tells you "Company X has high gallium exposure AND gallium is 98% sourced from China." The AI agents stitch that picture together from three independent government data sources.

---

## Architecture Overview

The application has three layers: a multi-agent backend (watsonx Orchestrate ADK), a data layer (SQLite database sourced from three government datasets), and a React frontend with a 3D globe visualization.

### High-Level Flow

1. User selects a company from the frontend dropdown
2. Frontend opens an SSE stream to the FastAPI backend
3. Backend runs local analytics in parallel with the cloud agent (Risk Orchestrator via Watson Orchestrate)
4. Trade Intel Agent queries trade data and computes country concentration
5. Corporate Exposure Agent searches USGS/EDGAR data for the company's mineral exposure and supply risk
6. Risk Orchestrator receives both outputs, computes a composite risk score, and returns structured JSON
7. Frontend renders trade flow arcs on the 3D globe, displays the risk score, and shows the agent workflow timeline
8. User can trigger disruption scenarios (e.g., China gallium export ban) which re-score and animate the globe
9. User can enter free-text custom scenarios for agent-driven analysis

---

## Agent Architecture

### Agent 1: Trade Intel Agent

- **Orchestration style:** ReAct
- **LLM:** groq/openai/gpt-oss-120b
- **Purpose:** Answers "Where does the US get its critical minerals, and how concentrated are those sources?"
- **Collaborators:** None (leaf agent)

**Tools:**

- `query_import_volumes` — Queries the `trade_data` table in SQLite (or calls back to FastAPI in cloud mode) for import volumes by mineral, grouped by source country for a given year.
- `compute_herfindahl` — Takes country-level import data and computes a Herfindahl-Hirschman Index (HHI) measuring concentration. Pure computation, no data access.
- `get_mineral_profile` — Queries `usgs_minerals`, `edgar_summary`, and `edgar_blind_spot_analysis` tables (or the `/api/mineral/profile/{mineral}` callback) for USGS mineral data enriched with EDGAR context.

**Output format:** JSON array of trade flow objects, each containing country name, mineral name, import volume in USD, percentage share of total US imports, and the HHI concentration index.

### Agent 2: Corporate Exposure Agent

- **Orchestration style:** ReAct
- **LLM:** groq/openai/gpt-oss-120b
- **Purpose:** Answers "Does this company depend on critical minerals, and do they acknowledge supply risk?"
- **Collaborators:** None (leaf agent)

**Tools:**

- `extract_mineral_dependencies` — Queries `edgar_mineral_company_matrix` (40 companies, direct presence/frequency) with fallback to `edgar_filing_details` (~1,020 companies by mineral mention). Returns mineral dependencies with severity ratings. Cloud mode calls `/api/company/dependencies/{company}`.
- `summarize_risk_section` — Generates company-centric or mineral-centric risk summaries from `edgar_filing_details`, `edgar_blind_spot_analysis`, `edgar_summary`, and `usgs_minerals`. Accepts optional `mineral_name` param for mineral-focused mode. Cloud mode calls `/api/risk-summary`.
- `search_edgar_10k` — Live SEC EDGAR full-text search API (efts.sec.gov) for real-time filing lookup. Uses `edgar_company_filings` table for CIK resolution. Supplemental freshness check on top of pre-scanned data.

**Output format:** JSON object containing the company name, list of minerals mentioned in filings, the generated risk summary text, and a corporate exposure score based on frequency and severity of mentions.

### Agent 3: Risk Orchestrator

- **Orchestration style:** Plan-Act (planner)
- **LLM:** groq/openai/gpt-oss-120b
- **Purpose:** Coordinates the two sub-agents, combines their outputs into a composite risk score, and handles disruption scenario simulation.
- **Collaborators:** trade_intel_agent, corporate_exposure_agent

**Tools (orchestrator-level):**

- `compute_composite_risk` — Takes trade concentration data from Agent 1 and corporate exposure data from Agent 2 and computes a weighted composite score from 0-100. Uses piecewise HHI normalization based on DOJ/FTC thresholds.
- `simulate_disruption` — Accepts a scenario definition (e.g., "China export ban on gallium") and re-computes the risk score with the specified country-mineral pair removed from the supply picture. Returns the updated score, the delta from baseline, and flow statuses (disrupted/stressed/active).
- `generate_mitigation_brief` — Stub awaiting Granite LLM integration. Intended to generate actionable mitigation plans based on disruption scenario results.

**Output format:** JSON object containing the company name, list of relevant minerals, array of trade flow objects (for globe rendering), the risk summary, the composite risk score with component breakdown, and optionally a scenario result.

### Why Plan-Act for the Orchestrator

The workflow is predictable and sequential: gather trade data, gather corporate data, score, optionally simulate. Plan-Act fits because the orchestrator knows the steps upfront and doesn't need exploratory reasoning. The sub-agents use ReAct because they may need to iterate (e.g., trying different search queries on EDGAR, or checking multiple minerals against the trade data).

---

## Data Sources — Verified and Validated

All data is stored in a single SQLite database (`data/mineralwatch.db`, ~3 MB) with 8 tables, migrated from source Excel files via `backend/migrate_to_db.py`.

### Source 1: USITC DataWeb (Trade Flow Data)

- **URL:** https://dataweb.usitc.gov
- **What it provides:** U.S. import volumes by HTS commodity code, broken down by source country, with annual granularity. Includes import value in USD (Customs Value).
- **Storage:** `trade_data` table, indexed on `(Mineral, Country)`. Source: `data/usitc_clean.xlsx`.
- **Columns:** Year, Mineral, Country, Customs Value (USD)

### Source 2: SEC EDGAR (Corporate Filing Data)

- **URL:** https://efts.sec.gov/LATEST/search-index (full-text search), https://data.sec.gov (structured API)
- **What it provides:** Filing metadata, mineral mentions in 10-K forms, company-mineral dependency matrices, and blind spot analysis.
- **Storage:** Five tables sourced from `data/edgar_mineral_results.xlsx`:
  - `edgar_filing_details` — Mineral mentions by company with form type and text snippets
  - `edgar_summary` — Per-mineral aggregates (EDGAR hits, unique companies, risk alignment)
  - `edgar_mineral_company_matrix` — 40 companies × 45 mineral columns (presence/frequency)
  - `edgar_blind_spot_analysis` — Minerals with supply risk but low EDGAR disclosure
  - `edgar_company_filings` — Company CIK mappings and filing metadata
- **Live supplement:** `search_edgar_10k` tool hits the SEC EDGAR API in real-time for freshness checks

### Source 3: USGS Mineral Commodity Summaries (Mineral Reference Data)

- **URL:** https://pubs.usgs.gov/publication/mcs2026
- **What it provides:** Supply risk ratings, top producers, substitutability assessments, fabrication stage classification, and HTS codes for 45+ semiconductor-critical minerals.
- **Storage:** `usgs_minerals` table sourced from `data/Semiconductor_Minerals_USGS_Map_With_HTS.xlsx`.
- **Key columns:** Fab Stage, Commodity Name, Supply Risk, Top Producer, HTS Code

**Note:** Some column names contain literal newlines (e.g., `"USGS Commodity Name\n(exact CSV name)"`). The shared `USGS_COL` constant in `_db.py` handles this. Matrix mineral columns use UPPERCASE with qualifiers (e.g., `"DIAMOND (INDUSTRIAL)*"`) — use `strip_mineral_qualifier()` before USGS lookups.

---

## The Data Connection Logic (How the App "Knows" Things)

No single data source tells you "NVIDIA has high gallium exposure AND gallium is 98% sourced from China." The agents connect three independent signals:

**Signal 1 — Industry-level mineral dependency (USGS):** The USGS data tells us which minerals are critical for semiconductor manufacturing. This is the baseline knowledge that gallium, germanium, tungsten, etc. matter for this industry.

**Signal 2 — Country-level trade concentration (USITC):** The trade data tells us where the US gets each mineral. This is country-level, not company-level. It answers "98% of US gallium imports come from China" regardless of which company we are analyzing.

**Signal 3 — Company-level risk disclosure (SEC EDGAR):** The filing data tells us whether a specific company mentions these minerals in their risk factors or supply chain disclosures. The `edgar_mineral_company_matrix` provides direct presence data for 40 companies; `edgar_filing_details` extends coverage to ~1,020 companies via mention-based analysis.

**What the agents infer:** The composite risk score combines these three signals. A company gets a high score when: (a) the minerals it depends on are highly concentrated in one source country, (b) the company explicitly acknowledges this dependency in its filings, and (c) the USGS data indicates low substitutability.

**Important caveat to acknowledge to judges:** The application does not know the exact tonnage of gallium that NVIDIA purchases. That data is proprietary. The system uses public disclosure signals as a proxy for direct procurement data. This is how real supply chain intelligence firms operate, and it is a valid approach, but it should be stated honestly.

---

## Risk Score Formula

The composite risk score is a number from 0-100 computed as a weighted combination of three components:

### Trade Concentration (40% weight)

Based on the Herfindahl-Hirschman Index (HHI) of country-of-origin concentration for each mineral the company depends on.

- HHI = sum of (country_share ^ 2) for all source countries
- Normalized to 0-100 via piecewise DOJ/FTC thresholds:
  - 0–1500 → 0–30 (unconcentrated)
  - 1500–2500 → 30–60 (moderately concentrated)
  - 2500–5000 → 60–85 (highly concentrated)
  - 5000–10000 → 85–100 (extremely concentrated)
- If a company depends on multiple minerals, the average HHI is computed across all relevant minerals

### Corporate Exposure (35% weight)

Based on severity-weighted USGS supply risk scores per mineral the company depends on.

- Draws from USGS supply risk ratings: LOW=20, MODERATE=50, HIGH=70, CRITICAL=90
- Weighted by mineral severity for the company
- Normalized to 0-100

### Substitutability Risk (25% weight)

Based on USGS assessments of whether alternative materials exist for semiconductor applications.

- Derived from the same USGS supply risk ratings
- LOW=20, MODERATE=50, HIGH=70, CRITICAL=90
- Normalized to 0-100

### Composite Calculation

```
composite_score = round(trade_concentration * 0.40 + corporate_exposure * 0.35 + substitutability_risk * 0.25)
```

### Scenario Re-scoring

When a disruption scenario is triggered (e.g., "China export ban on gallium"):

1. Remove the banned country from the trade data for the specified mineral(s)
2. Recalculate the HHI on remaining countries — trade score is floored at baseline (disruption can never improve it) plus a supply gap penalty
3. Increase the corporate exposure component by a fixed uplift (15 per mineral disrupted, capped at 100)
4. Recalculate the composite score
5. Return the delta (new score minus baseline score) and flow statuses (disrupted/stressed/active)

**Multi-mineral disruption:** `simulate_multi_disruption()` handles scenarios where multiple minerals from a single country are disrupted simultaneously (e.g., "China bans all mineral exports"). Scales corporate uplift by `15 × num_minerals`.

**Custom scenario extraction:** Free-text scenario input is parsed by `_extract_country_mineral()` which detects broad patterns ("all minerals", "all exports") returning `["__ALL__"]` sentinel, or collects individually matched minerals. `_infer_disruption_pct()` parses scenario severity: "ban/embargo/block/halt/stop" → 100%, "restrict/limit/reduce" → 50%, default 75%.

---

## Frontend Architecture

### Technology Stack

- React 19 (functional components with hooks)
- TypeScript + Vite (with `@` → `./src` path alias)
- TailwindCSS v4 (utility styling)
- react-globe.gl (3D globe visualization, built on Three.js)
- shadcn/ui (Radix primitives)
- Framer Motion (animations)
- Axios + TanStack React Query (data fetching)
- react-markdown (agent output rendering)
- IBM Plex fonts
- Dark theme with risk-level color coding (red/amber/green)

### Layout: 12-Column Grid Dashboard

The interface is a 12-column, 6-row grid layout (`gap-4`) optimized for projector demos:

**Left Column (`col-span-3 row-span-6`):**

- **CompanySelector** — Dropdown to pick a company for analysis (dynamically loaded from backend `GET /companies`)
- **MetricsPanel** — Composite risk score with animated value transitions, trade concentration, corporate exposure, and substitutability breakdown. Hover tooltips on each metric explaining its computation. Risk Score value color-coded by severity (red >70, amber 30–70, green <30). Shows disrupted scores with delta indicators during simulation.
- **ScenariosPanel** — Dynamic disruption scenario cards generated from trade concentration data (minerals with >30% single-country share). Click-to-simulate with reset. Custom free-text scenario input that invokes the cloud agent via SSE.

**Center Globe (`col-span-6 row-span-4`):**

- **GlobeView** — 3D interactive globe with supply route arcs colored by risk level:
  - Arc thickness proportional to risk: high=1.2, elevated=0.8, low=0.4
  - Arc animation speed inversely proportional to risk: high=4s slow, elevated=2.5s, low=1.2s fast
  - Staggered arc launches via `arcDashInitialGap`
  - Disrupted/stressed/active arc states during simulation (disrupted uses `rgba()` for transparent colors)
  - Expandable legend with line-thickness explanations and disruption states
  - Arc speed multiplier control (0.5x–2x) in bottom-right corner

**Bottom Table (`col-span-6 row-span-2`):**

- **RiskTable** — Sortable trade flow table with concentration bars (click column headers to sort). Threshold markers at 30% and 70% on concentration bars. Disrupted/stressed flow count badges in header during simulation.

**Right Column (`col-span-3 row-span-6`):**

- **AgentWorkflow** — Real-time agent execution timeline streamed via SSE from `/api/analyze-stream/{company}`. Shows 4 stages: orchestrator_planning → trade_intel → corporate_exposure → orchestrator_scoring → complete. Expandable full agent output on steps with truncated content (animated expand/collapse). Markdown rendering for agent output.

### Globe Visualization Details

**Arc rendering:** Each arc represents a trade flow from a mineral-producing country to the United States. The arc properties encode data:

- **Thickness (stroke):** Proportional to risk level. High-risk arcs (>50% share) are visually dominant.
- **Color:** Encodes risk level. Red (#ef4444) for critical concentration (share > 50%), Amber (#f59e0b) for elevated (share > 20%), Green (#22c55e) for low concentration.
- **Animation:** Arcs use dash animation to create a "flowing" effect from source country toward the US. Higher-risk arcs flow slower (conveying danger/weight), lower-risk arcs flow faster.

**Country coordinate mapping:** `Frontend/src/data/countryCoords.json` maps ~130 country names to their geographic centroid lat/lng. Covers all countries appearing in the USITC trade data.

### Globe Texture

Uses a dark earth texture — the dark background makes colored arcs and country highlights pop dramatically on a projector screen. Glowing colored arcs on a dark surface have significantly more visual impact than the same arcs on a bright blue background.

### UX State Machine

**State: Empty (app load)**

- Globe auto-rotates slowly
- Left panel shows company dropdown with placeholder text
- No arcs, no metrics displayed

**State: Loading (company selected)**

- Right panel: AgentWorkflow streams real-time SSE events from `GET /api/analyze-stream/{company}`, showing 4 stages progressing through pending → active → completed
- Globe: Loading overlay displayed
- Agent trace messages update live: "Risk Orchestrator: Planning analysis...", "Trade Intelligence Agent: Querying trade flows...", etc.

**State: Results (agents complete)**

- Globe: Trade flow arcs populate from source countries to USA, colored by risk level
- Left panel: MetricsPanel shows composite score and breakdown (trade, corporate, substitutability)
- Left panel: ScenariosPanel populates with dynamic scenario cards generated from concentrated trade flows
- Right panel: AgentWorkflow shows all 4 steps as completed with timestamps and trace data
- Bottom: RiskTable shows sortable trade flow data

**State: Scenario Active (disruption simulated)**

- User clicks a scenario card → triggers `POST /api/simulate`
- Globe: Disrupted arc fades to ghost red (transparent, no dash animation). Stressed arcs (same mineral, other countries) thicken and turn amber. Active arcs (other minerals) unchanged.
- Left panel: MetricsPanel shows disrupted scores with delta indicators (e.g., +5). ScenariosPanel highlights the active scenario card.
- User clicks "Reset" to return to baseline scores and normal arc rendering.

**State: Custom Scenario (free-text analysis)**

- User enters a free-text scenario description in the ScenariosPanel input
- SSE stream opens to `GET /api/custom-scenario-stream/{company}?scenario=` for agent-driven analysis
- Cloud agent processes the scenario and returns simulation results
- Same visual updates as Scenario Active state

### Frontend-to-Backend Communication

The React frontend communicates with the FastAPI backend at `localhost:8000` via three channels:

1. **SSE streaming** (`EventSource` → `GET /api/analyze-stream/{company}`) — real-time agent workflow updates via `useAnalysisStream` hook
2. **SSE streaming** (`EventSource` → `GET /api/custom-scenario-stream/{company}`) — custom scenario analysis via `useCustomScenarioStream` hook
3. **REST queries** (Axios + TanStack React Query) — company list, scenarios, mineral data
4. **REST mutations** (Axios + TanStack `useMutation`) — disruption simulation via `POST /api/simulate`

The backend returns structured JSON with a defined schema (company, minerals, trade_flows array, score breakdown). The frontend maps trade flows to globe arc data using `countryCoords.json` for geographic coordinates.

### Color System

Consistent color language across all UI elements:

- Critical risk: Red (#ef4444) — arcs with >50% share, high-risk countries, danger indicators
- Elevated risk: Amber (#f59e0b) — moderate concentration, stressed suppliers in scenario mode
- Low risk: Green (#22c55e) — diversified supply, low concentration
- Disrupted: Ghost red (rgba(239, 68, 68, 0.4)) — faded arcs for banned trade routes
- Neutral: Slate/gray for UI chrome, text, borders

Use this palette on arcs, country highlights, score card indicators, breakdown bars, and scenario buttons. A judge should be able to glance at the screen and understand the risk picture without reading text.

---

## Backend Architecture

### FastAPI App (`main.py`)

CORS configured for `localhost:5173`. Full endpoint list:

**Core endpoints:**
- `GET /` — health check message
- `GET /health` — status ok
- `GET /companies` — list all companies in the DB

**Analysis endpoints:**
- `GET /analyze/{company}` — full risk analysis (trade + corporate + substitutability scores)
- `GET /api/analyze-stream/{company}` — SSE endpoint streaming staged analysis events (orchestrator_planning → trade_intel → corporate_exposure → orchestrator_scoring → complete)
- `GET /api/custom-scenario-stream/{company}?scenario=` — SSE endpoint for free-text custom scenario analysis via cloud agent

**Mineral & company data endpoints:**
- `GET /api/minerals/list` — list all tracked minerals
- `GET /api/company/minerals/{company}` — minerals for a specific company
- `GET /api/mineral/risk/{mineral}` — trade concentration & supply risk for a mineral
- `GET /api/company/summary/{company}` — company name + risk summary snippet
- `GET /api/company/scenarios/{company}` — dynamic disruption scenarios based on trade concentration

**Simulation:**
- `POST /api/simulate` — accepts `{company, country, mineral, disruption_pct?}`, returns disrupted risk scores with flow statuses

**ADK tool callback endpoints** (used by cloud-deployed tools via HTTP):
- `GET /api/mineral/trade/{mineral}?year=` — import volumes by country for a mineral
- `GET /api/mineral/profile/{mineral}` — structured USGS/EDGAR mineral profile
- `GET /api/company/dependencies/{company}` — mineral dependencies with severity
- `GET /api/risk-summary?company=&mineral=` — risk summary (company-centric or mineral-centric)
- `GET /api/edgar/cik/{company}` — CIK lookup from EDGAR data

**Diagnostics:**
- `GET /api/agent-diagnostics` — debug endpoint: env var status, agent UUID resolution, callback reachability

### Analytics Engine (`analytics.py`)

Risk analysis engine querying `mineralwatch.db`. Key functions:

- `resolve_company_name(name)` — normalizes company names for callback endpoints. Handles LLM-reformulated names (e.g., "Amazon.com Inc" → "AMAZON COM INC") by stripping punctuation and doing case-insensitive matching.
- `_get_trade_data_for_company(company, conn, minerals)` — trade flows + HHI computation
- `_get_corporate_data_for_company(conn, minerals)` — USGS-based corporate + substitutability scores
- `analyze_company(company)` — full analysis combining both helpers
- `get_company_scenarios(company)` — generates up to 5 disruption scenarios from concentrated trade flows (minerals with >30% single-country share)
- `simulate_company_disruption(company, country, mineral, disruption_pct)` — single-mineral disruption
- `simulate_multi_disruption(company, country, minerals_to_disrupt, disruption_pct)` — multi-mineral disruption
- ADK callback helpers: `get_mineral_trade_flows()`, `get_mineral_profile_data()`, `get_company_dependencies()`, `get_risk_summary()`, `lookup_edgar_cik()`

### Agent Client (`agent_client.py`)

IBM Watson Orchestrate RunClient integration for invoking the deployed `risk_orchestrator` agent. Features:

- IAM authentication with agent UUID resolution
- Polling for run completion
- Falls back to keyword-based extraction + local simulation if the agent is unavailable
- Apology/refusal detection (`_is_agent_useful()`) — when the cloud LLM returns conversational refusals instead of tool outputs, the local analytics summary is preserved and the result includes `agent_enriched: false`
- SSE events include `full_output` field with untruncated agent text when the response exceeds the display truncation threshold (300 chars for standard analysis, 600 chars for custom scenarios)

---

## ADK Tools (`backend/adk-project/tools/`)

Tools support dual-mode data access: local SQLite (default) or HTTP callbacks to the FastAPI backend when `BACKEND_API_URL` is set (cloud deployment). The switch is controlled by `_api.py:is_api_mode()` which resolves the URL from either an Orchestrate `key_value_creds` connection (`app_id: backend_api`) or the `BACKEND_API_URL` env var.

| Tool | Source Table(s) | Purpose |
|------|----------------|---------|
| `query_import_volumes` | `trade_data` | Import volumes by mineral & country |
| `compute_herfindahl` | (pure computation) | HHI concentration index from trade flows |
| `get_mineral_profile` | `usgs_minerals`, `edgar_summary`, `edgar_blind_spot_analysis` | USGS mineral data + EDGAR enrichment |
| `extract_mineral_dependencies` | `edgar_mineral_company_matrix`, `edgar_filing_details`, `usgs_minerals` | Company mineral exposures with severity (matrix for 40 companies, filing_details fallback for ~1,020) |
| `summarize_risk_section` | `edgar_filing_details`, `edgar_blind_spot_analysis`, `edgar_summary`, `usgs_minerals` | Company or mineral-centric risk summary with exposure score |
| `compute_composite_risk` | `usgs_minerals` | Weighted composite score with piecewise HHI normalization |
| `search_edgar_10k` | (live SEC EDGAR API) + `edgar_company_filings` for CIK lookup | Real-time filing search (supplemental freshness check) |
| `simulate_disruption` | (pure computation) | Disruption scenario modeling |
| `generate_mitigation_brief` | (stub, not wired to any agent) | Mitigation recommendations — awaiting Granite LLM |

**Shared helpers** (local dev only — cloud tools inline these via try/except fallback):
- `_db.py`: `get_db_conn()`, `strip_mineral_qualifier()`, `USGS_COL`, `DEFAULT_RISK_SCORE`
- `_api.py`: `is_api_mode()`, `api_get()`, `BACKEND_CONNECTION` (credential declaration for `@tool()` decorators)

**Cloud compatibility:** Each tool file wraps `_api`/`_db` imports in `try/except (ImportError, ModuleNotFoundError)` with inlined fallback definitions. Watson Orchestrate imports tools as standalone files (no access to sibling modules), so the fallback provides `BACKEND_CONNECTION`, `is_api_mode()`, `api_get()`, constants, and a `get_db_conn()` stub that raises `RuntimeError`.

---

## Cloud Deployment (IBM Watson Orchestrate)

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

---

## Database (`data/mineralwatch.db`)

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

Source Excel files in `data/`: `Semiconductor_Minerals_USGS_Map_With_HTS.xlsx`, `edgar_mineral_results.xlsx`, `usitc_clean.xlsx`.

---

## Project File Structure

```
roq/
├── .env                              # IBM Cloud API keys, Orchestrate config, optional BACKEND_API_URL
├── CLAUDE.md                         # Claude Code project instructions
├── SYSTEM_DESIGN.md                  # This document
├── README.md                         # Project overview and setup
├── data/
│   ├── mineralwatch.db               # SQLite database (~3 MB, 8 tables)
│   ├── Semiconductor_Minerals_USGS_Map_With_HTS.xlsx
│   ├── edgar_mineral_results.xlsx
│   └── usitc_clean.xlsx
├── backend/
│   ├── main.py                       # FastAPI app with all endpoints
│   ├── analytics.py                  # Risk analysis engine (queries mineralwatch.db)
│   ├── agent_client.py               # Watson Orchestrate RunClient integration
│   ├── migrate_to_db.py              # Excel → SQLite migration script
│   ├── test_tools.py                 # ADK tool smoke tests (mocks IBM SDK)
│   ├── requirements.txt              # Python dependencies
│   ├── .venv/                        # Python virtual environment
│   └── adk-project/
│       ├── agents/
│       │   ├── trade_intel_agent.yaml
│       │   ├── corporate_exposure_agent.yaml
│       │   └── risk_orchestrator.yaml
│       └── tools/
│           ├── _api.py               # Shared: dual-mode helper (local DB / HTTP callback)
│           ├── _db.py                # Shared: SQLite connection, constants
│           ├── query_import_volumes.py
│           ├── compute_herfindahl.py
│           ├── get_mineral_profile.py
│           ├── extract_mineral_deps.py
│           ├── summarize_risk_section.py
│           ├── compute_composite_risk.py
│           ├── search_edgar_10k.py
│           ├── simulate_disruption.py
│           └── generate_mitigation.py  # Stub — awaiting Granite LLM
├── Frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── public/
│   │   └── roq-icon.png
│   └── src/
│       ├── App.tsx
│       ├── pages/
│       │   └── Index.tsx             # Main dashboard (12-col grid layout)
│       ├── components/
│       │   ├── CompanySelector.tsx
│       │   ├── MetricsPanel.tsx      # Risk score + breakdown with tooltips
│       │   ├── GlobeView.tsx         # 3D globe with arc rendering
│       │   ├── AgentWorkflow.tsx     # SSE-driven agent execution timeline
│       │   ├── ScenariosPanel.tsx    # Disruption scenario cards + custom input
│       │   ├── RiskTable.tsx         # Sortable trade flow table
│       │   └── ui/
│       │       └── markdown.tsx      # Shared Markdown renderer
│       ├── hooks/
│       │   ├── useAnalysisStream.ts  # SSE hook for /api/analyze-stream
│       │   └── useCustomScenarioStream.ts  # SSE hook for custom scenarios
│       ├── lib/
│       │   └── api.ts               # Axios client + TypeScript interfaces
│       └── data/
│           ├── countryCoords.json    # ~130 country centroid coordinates
│           └── simulatedData.ts      # Legacy mock data (unused)
└── Frontend/index.html
```

---

## Demo Script (3 Minutes)

**0:00 — Context (15 seconds)**
"Semiconductor supply chains depend on a handful of critical minerals. China controls 98% of gallium production. No tool maps how this concentration risk compounds across a specific company's supply chain. Roq changes that."

**0:15 — Select Company (30 seconds)**
Select a company from the dropdown. Point out the AgentWorkflow panel as both sub-agents begin working. "Our risk orchestrator dispatches two specialized agents — one analyzing US trade data, one scanning USGS supply risk and SEC filings."

**0:45 — Results Appear (45 seconds)**
Arcs populate the globe. "See this thick red arc from China? That represents 98% of US gallium imports flowing from a single country. Our corporate exposure agent cross-references USGS supply risk data with SEC filing disclosures to identify material dependencies." Point to the risk score and walk through the three breakdown components. Show the RiskTable with sortable concentration bars.

**1:30 — Scenario Simulation (45 seconds)**
Click a scenario card (e.g., "China Gallium Export Ban"). The arc fades to ghost red, stressed arcs thicken, score jumps. "Watch — when we simulate a Chinese export ban, that trade route disappears. The remaining suppliers are stressed. Our metrics update in real-time showing the delta." Optionally type a custom free-text scenario to demonstrate agent-driven analysis.

**2:15 — Architecture (30 seconds)**
"Three AI agents, each with specialized tools, orchestrated through IBM watsonx Orchestrate. The system uses three independent US government data sources — USITC trade data, SEC EDGAR filings, and USGS mineral intelligence — to build a picture no single source can provide. Every agent decision is traceable."

**2:45 — Close (15 seconds)**
"Roq turns public data into actionable intelligence. It helps semiconductor companies prepare for supply chain disruptions before they happen, not after."

---

## Key Technical Decisions and Rationale

**Why SQLite instead of raw CSVs:** Pre-downloaded Excel files are migrated into a single SQLite database (`mineralwatch.db`) for fast indexed queries, JOIN support across data sources, and simpler deployment. The `migrate_to_db.py` script makes the migration reproducible.

**Why dual-mode tools (local DB + HTTP callbacks):** Watson Orchestrate cloud can't access the local SQLite file. Tools detect their environment via `_api.py:is_api_mode()` and either query the DB directly (local dev) or make HTTP callbacks to the FastAPI backend (cloud). Each tool file inlines fallback definitions for cloud compatibility since Orchestrate imports tools as standalone files.

**Why Groq-served gpt-oss-120b instead of Granite:** The 120B parameter open-source model served via Groq provides fast inference with native tool-calling support that proved more reliable for multi-step agent reasoning than smaller models. The watsonx Orchestrate ADK platform handles the orchestration regardless of which LLM powers the agents.

**Why Plan-Act for the orchestrator and ReAct for sub-agents:** The orchestrator's workflow is predictable (gather trade data → gather corporate data → score → optionally simulate), making Plan-Act appropriate. The sub-agents may need to iterate (try different EDGAR search queries, check multiple minerals) making ReAct's explore-observe-act loop more flexible.

**Why react-globe.gl instead of a 2D map:** The 3D globe with animated arcs is the visual differentiator. It communicates geographic concentration risk instantly and creates a memorable demo moment. react-globe.gl handles WebGL rendering with a React-friendly API.

**Why dark globe texture:** The dark background makes colored arcs and country highlights dramatically more visible, especially on a projector in a hackathon presentation room. Glowing colored arcs on a dark surface have significantly more visual impact than the same arcs on a bright blue background.

**Why concurrent local analytics + cloud agent:** The SSE streaming endpoint runs local analytics in parallel with the cloud agent call. Local analytics provide guaranteed fast results; the cloud agent enriches with additional reasoning when available. If the agent is slow or returns refusals, the local results are still complete.

**Why apology/refusal detection:** Cloud LLMs sometimes return conversational responses ("I'd be happy to help...") instead of structured tool outputs. `_is_agent_useful()` detects these patterns so the system can fall back to local analytics gracefully, flagging results with `agent_enriched: false`.
