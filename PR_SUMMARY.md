# PR Summary: Full Frontend-Backend Integration

**Branch:** `feature/adk-cloud-deploy-fixes` → `main`

---

## What Changed

Connected all 6 dashboard panels to real backend computation, completing the system design flow: company selection → agent workflow streaming → globe/metrics render → scenario simulation → re-scored visualization.

### Backend: Staged Analysis & Simulation Engine

- **Decomposed** `analyze_company` into `_get_trade_data_for_company()` and `_get_corporate_data_for_company()` helpers for SSE streaming
- **New:** `get_company_scenarios(company)` — generates up to 5 disruption scenarios from minerals with >30% single-country trade concentration
- **New:** `simulate_company_disruption(company, country, mineral)` — removes a country/mineral pair, recomputes HHI, uplifts corporate score by +15, marks flows as disrupted/stressed/active
- **New endpoints:**
  - `GET /api/analyze-stream/{company}` — SSE streaming 4-stage analysis (orchestrator → trade intel → corporate exposure → scoring)
  - `GET /api/company/scenarios/{company}` — dynamic scenario cards
  - `POST /api/simulate` — disruption simulation with re-scored results

### Frontend: Live Agent Workflow & Scenario Simulation

- **New:** `useAnalysisStream` SSE hook — replaces `useQuery(analyze)` with real-time `EventSource` streaming
- **AgentWorkflow** — now shows live agent stages (pending → active → completed) instead of hardcoded mock data
- **ScenariosPanel** — dynamic cards with concentration bars, click-to-simulate, active highlight, reset button (replaces static sparkline cards)
- **GlobeView** — derives points from arcs prop, function accessors for `arcStroke`/`arcDashAnimateTime`, scenario-aware rendering (ghost arcs for disrupted, thick amber for stressed)
- **MetricsPanel** — shows disrupted scores + delta indicators during active simulation
- **Index.tsx** — full rewire with SSE hook, scenario state, simulation mutation, scenario-aware arc coloring
- **countryCoords.json** — expanded from 19 → ~130 countries to cover all trade partners

### Documentation

- **CLAUDE.md** — updated to reflect all new endpoints, decomposed analytics functions, SSE hook, `.venv` usage, and panel descriptions
- **SYSTEM_DESIGN.md** — updated UX state machine and frontend-to-backend communication sections to reflect implemented state

## Files Changed (13)

| Area | Files |
|------|-------|
| Backend | `analytics.py`, `main.py` |
| Frontend (new) | `src/hooks/useAnalysisStream.ts` |
| Frontend (modified) | `AgentWorkflow.tsx`, `ScenariosPanel.tsx`, `GlobeView.tsx`, `MetricsPanel.tsx`, `Index.tsx`, `api.ts` |
| Data | `countryCoords.json` |
| Docs | `CLAUDE.md`, `SYSTEM_DESIGN.md`, `PR_SUMMARY.md` |
