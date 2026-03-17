<p align="center">
  <img src="Roq_Icon.png" alt="Roq" width="220" />
</p>

<h1 align="center">Roq</h1>

<p align="center">
  <strong>AI-powered supply chain risk intelligence for semiconductor and electronics manufacturers</strong>
</p>

---

Roq is a hackathon project built for IBM that surfaces hidden mineral supply chain risks buried in SEC filings, USGS data, and global trade flows — then lets you simulate disruptions in real time using an AI agent orchestration backend powered by IBM Watson Orchestrate.

---

## Demo

<a href ="https://docs.google.com/presentation/d/1PLwCnWXeAwBH3DNUQnuxMnW83VDSmdfodx-XNTys2fg/edit?usp=sharing"> Slides + Demo Video </a>

---

## What It Does

- **Risk Scoring** — Computes a composite risk score per company across three dimensions: trade concentration (HHI), corporate exposure (SEC filings), and mineral substitutability
- **3D Globe Visualization** — Animates live supply routes by risk level with color-coded arcs and risk-proportional thickness/speed
- **AI Agent Workflow** — Streams a real-time agent execution timeline as IBM Watson Orchestrate agents analyze trade flows and corporate filings in parallel
- **Disruption Simulation** — Click a scenario card (or type a free-text scenario) to instantly re-score a company with a country/mineral disruption applied
- **Dynamic Scenarios** — Auto-generates disruption scenarios from trade concentration data (minerals with >30% single-country share)

---

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| Frontend | React 19, TypeScript, Vite, TailwindCSS v4, shadcn/ui, Framer Motion |
| 3D Globe | react-globe.gl, Three.js |
| Data Fetching | Axios, TanStack React Query, SSE (EventSource) |
| Backend | FastAPI, Python, SQLite |
| AI Agents | IBM Watson Orchestrate ADK, Groq (`gpt-oss-120b`) |
| Data Sources | USGS mineral data, SEC EDGAR filings, USITC trade data |

---

## Getting Started

### Prerequisites

- Node.js 18+
- Python 3.11+
- An IBM Watson Orchestrate account with a deployed `risk_orchestrator` agent

### 1. Clone & configure environment

```bash
git clone <repo-url>
cd ibm_hacks
```

Create a `.env` file in the project root:

```env
IBM_API_KEY=your_ibm_api_key
ORCHESTRATE_APIKEY=your_orchestrate_apikey
ORCHESTRATE_IAM_APIKEY=your_orchestrate_iam_apikey
ORCHESTRATE_URL=your_orchestrate_url
ORCHESTRATE_AUTH_TYPE=iam

# Optional: public backend URL for cloud agent callbacks (e.g. ngrok tunnel)
BACKEND_API_URL=https://your-public-backend-url
```

### 2. Backend setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Build the SQLite database from Excel source files
python migrate_to_db.py

# Start the API server
uvicorn main:app --reload
# → http://localhost:8000
```

### 3. Frontend setup

```bash
cd Frontend
npm install
npm run dev
# → http://localhost:5173
```

### 4. Run tests

```bash
cd backend && .venv/bin/python test_tools.py
```

---

## Architecture

### Frontend

Single-page dashboard at `/` using a 12-column, 6-row grid layout.

**Dashboard Panels** (`src/pages/Index.tsx`):

| Panel | Description |
|-------|-------------|
| `CompanySelector` | Dropdown to select a company for analysis |
| `MetricsPanel` | Risk score, trade concentration, corporate exposure, substitutability — shows disrupted deltas during simulation |
| `GlobeView` | 3D globe with supply arcs colored/sized/animated by risk level; supports disrupted/stressed/active arc states |
| `AgentWorkflow` | Real-time agent execution timeline streamed via SSE; expandable full agent output on truncated steps |
| `ScenariosPanel` | Auto-generated disruption scenario cards; click-to-simulate or enter a free-text custom scenario |
| `RiskTable` | Sortable trade flow table with concentration bars |

**Key files:**
- `src/hooks/useAnalysisStream.ts` — SSE hook managing 4-step agent workflow state
- `src/hooks/useCustomScenarioStream.ts` — SSE hook for free-text custom scenario analysis
- `src/lib/api.ts` — Axios API client with TypeScript interfaces
- `src/data/countryCoords.json` — ~130 country centroid coordinates for globe arc rendering

---

### Backend

FastAPI app (`backend/main.py`) with CORS for `localhost:5173`.

**Key endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/companies` | List all companies in the DB |
| GET | `/analyze/{company}` | Full risk analysis (trade + corporate + substitutability) |
| GET | `/api/company/scenarios/{company}` | Auto-generated disruption scenarios |
| POST | `/api/simulate` | Disruption re-scoring with flow status updates |
| GET | `/api/analyze-stream/{company}` | SSE stream of staged agent analysis |
| GET | `/api/custom-scenario-stream/{company}` | SSE stream for free-text scenario via cloud agent |
| GET | `/api/agent-diagnostics` | Debug endpoint: env vars, agent UUID, callback reachability |

**Risk scoring model** (`backend/analytics.py`):

| Component | Weight | Method |
|-----------|--------|--------|
| Trade Risk | 40% | HHI normalized via DOJ/FTC piecewise thresholds |
| Corporate Risk | 35% | Severity-weighted USGS supply risk scores |
| Substitutability Risk | 25% | USGS ratings mapped to 20/50/70/90 |

---

### AI Agents (`backend/adk-project/`)

Three agents using `groq/openai/gpt-oss-120b` deployed to IBM Watson Orchestrate:

| Agent | Style | Purpose |
|-------|-------|---------|
| `trade_intel_agent` | ReAct | Trade flow analysis & HHI concentration |
| `corporate_exposure_agent` | ReAct | SEC filing analysis & corporate mineral risk |
| `risk_orchestrator` | Plan-Act | Coordinates sub-agents, computes final composite score |

**ADK Tools** (`backend/adk-project/tools/`):

| Tool | Purpose |
|------|---------|
| `query_import_volumes` | Import volumes by mineral & country |
| `compute_herfindahl` | HHI concentration index computation |
| `get_mineral_profile` | USGS mineral data + EDGAR enrichment |
| `extract_mineral_dependencies` | Company mineral exposures with severity |
| `summarize_risk_section` | Company or mineral-centric risk summary |
| `compute_composite_risk` | Weighted composite score |
| `search_edgar_10k` | Live SEC EDGAR filing search |
| `simulate_disruption` | Disruption scenario modeling |

Tools support **dual-mode data access**: local SQLite in development, or HTTP callbacks to the FastAPI backend when deployed to the cloud (`BACKEND_API_URL`).

---

### Database (`data/mineralwatch.db`)

SQLite (~3 MB), migrated from Excel via `backend/migrate_to_db.py`.

| Table | Source | Contents |
|-------|--------|----------|
| `usgs_minerals` | USGS | Supply risk ratings, top producers, HTS codes |
| `trade_data` | USITC | Import volumes by year, mineral, and country |
| `edgar_filing_details` | EDGAR scan | Mineral mentions in 10-K filings by company |
| `edgar_summary` | EDGAR scan | Mineral-level EDGAR hit counts and risk alignment |
| `edgar_mineral_company_matrix` | EDGAR scan | Company × 45 mineral presence matrix |
| `edgar_blind_spot_analysis` | EDGAR scan | Supply risk assessments and recommended actions |
| `edgar_company_filings` | EDGAR scan | CIK lookup and filing metadata |

---

### Cloud Deployment (IBM Watson Orchestrate)

```bash
# 1. Register the backend URL as a connection
orchestrate connections add --app-id backend_api
orchestrate connections set-credentials --app-id backend_api --env draft --entries "BACKEND_API_URL=https://your-backend-url"
orchestrate connections set-credentials --app-id backend_api --env live --entries "BACKEND_API_URL=https://your-backend-url"

# 2. Import tools
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

For local dev with ngrok: set `BACKEND_API_URL` in `.env` and tunnel port 8000.

---

## Project Structure

```
ibm_hacks/
├── Frontend/               # React + Vite frontend
│   └── src/
│       ├── components/     # Dashboard panels and UI
│       ├── hooks/          # SSE streaming hooks
│       ├── lib/            # API client
│       └── data/           # Country coords, static assets
├── backend/
│   ├── main.py             # FastAPI app + all endpoints
│   ├── analytics.py        # Risk engine + DB queries
│   ├── agent_client.py     # Watson Orchestrate RunClient integration
│   ├── migrate_to_db.py    # Excel → SQLite migration script
│   └── adk-project/
│       ├── agents/         # Agent YAML definitions
│       └── tools/          # ADK Python tools
└── data/
    ├── mineralwatch.db     # SQLite database
    └── *.xlsx              # Source Excel files
```

---

Built for the IBM Hackathon · March 2026
