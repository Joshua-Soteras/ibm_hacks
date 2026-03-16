# MineralWatch — System Design Document

## Project Overview

MineralWatch is a multi-agent AI application that assesses semiconductor companies' exposure to critical mineral supply chain disruptions. It combines U.S. government trade data, SEC corporate filings, and USGS mineral intelligence into a unified risk score, visualized on an interactive 3D globe.

**One-liner:** Multi-agent supply chain risk intelligence for critical semiconductor minerals — with scenario simulation for export disruption events.

**Hackathon track:** Semiconductor Manufacturing — specifically the "AI agent that monitors supply chain risks and recommends mitigation strategies" use case.

**IBM Stack:** watsonx Orchestrate ADK + Granite 3.3 8B Instruct + ADK Knowledge Bases + Langfuse

---

## Problem Statement

Semiconductor manufacturers have no automated way to assess their compound exposure to mineral supply disruptions. A company might know it uses gallium, but not that 98% of US gallium imports originate from a single country, or that their own 10-K annual filing already flags this as a material risk. When an export ban drops, they are reactive instead of prepared.

The core insight: no single public data source tells you "Company X has high gallium exposure AND gallium is 98% sourced from China." The AI agents stitch that picture together from three independent government data sources.

---

## Architecture Overview

The application has three layers: a multi-agent backend (watsonx Orchestrate ADK), a data layer (three government data sources), and a React frontend with a 3D globe visualization.

### High-Level Flow

1. User selects a company from the frontend dropdown
2. Frontend sends a query to the watsonx Orchestrate ADK backend
3. The Risk Orchestrator agent dispatches two sub-agents in parallel
4. Trade Intel Agent queries pre-downloaded USITC import data and computes country concentration
5. Corporate Exposure Agent searches SEC EDGAR for the company's 10-K filings and extracts mineral mentions using Granite
6. Risk Orchestrator receives both outputs, computes a composite risk score, and returns structured JSON
7. Frontend renders trade flow arcs on the 3D globe, displays the risk score, and shows the 10-K summary
8. User can trigger disruption scenarios (e.g., China gallium export ban) which re-score and animate the globe

---

## Agent Architecture

### Agent 1: Trade Intel Agent

- **Orchestration style:** ReAct
- **LLM:** watsonx/ibm/granite-3-8b-instruct
- **Purpose:** Answers "Where does the US get its critical minerals, and how concentrated are those sources?"
- **Collaborators:** None (leaf agent)

**Tools:**

- `query_import_volumes` — Reads pre-downloaded USITC CSV files filtered by HTS commodity code. Accepts a mineral name, maps it to the correct HTS code, loads the corresponding CSV with pandas, and returns import volumes grouped by country of origin for the requested time range.
- `compute_herfindahl` — Takes the country-level import data and computes a Herfindahl-Hirschman Index (HHI) measuring concentration. The formula is: sum of squared market shares across all source countries. Returns a value between 0 and 1, where 1.0 means a single country supplies 100%.
- `get_mineral_profile` — Queries the USGS knowledge base (RAG) for a given mineral and returns key facts: world production leaders, U.S. import reliance percentage, known substitutes, and strategic importance rating.

**Output format:** JSON array of trade flow objects, each containing country name, mineral name, import volume in kg, percentage share of total US imports, and the HHI concentration index.

### Agent 2: Corporate Exposure Agent

- **Orchestration style:** ReAct
- **LLM:** watsonx/ibm/granite-3-8b-instruct
- **Purpose:** Answers "Does this company depend on critical minerals, and do they acknowledge supply risk?"
- **Collaborators:** None (leaf agent)

**Tools:**

- `search_edgar_10k` — Hits the SEC EDGAR full-text search API (efts.sec.gov/LATEST/search-index) with a query combining the company name or CIK number with mineral-related keywords. Filters to 10-K form type. Returns filing metadata including accession numbers and URLs to the full filing documents. This API is free, requires no authentication, and can be hit live during the demo.
- `extract_mineral_dependencies` — Takes a filing URL from the EDGAR search results, fetches the filing HTML, and uses Granite to perform named entity recognition on the text. Identifies mentions of critical minerals (gallium, germanium, tungsten, cobalt, rare earths) and their context (risk factor section, supply chain discussion, etc.). Returns a list of mineral mentions with their surrounding context and the section of the filing they appear in.
- `summarize_risk_section` — Takes the extracted filing text around mineral mentions and uses Granite to generate a concise 2-3 sentence summary of the company's disclosed supply chain risks related to critical minerals. This summary is displayed directly in the frontend.

**Output format:** JSON object containing the company name, list of minerals mentioned in filings, number of filings with mentions, the generated risk summary text, and a corporate exposure score (0-1) based on frequency and severity of mentions.

### Agent 3: Risk Orchestrator

- **Orchestration style:** Plan-Act
- **LLM:** watsonx/ibm/granite-3-8b-instruct
- **Purpose:** Coordinates the two sub-agents, combines their outputs into a composite risk score, and handles disruption scenario simulation.
- **Collaborators:** trade_intel_agent, corporate_exposure_agent

**Tools (orchestrator-level):**

- `compute_composite_risk` — Takes the trade concentration data from Agent 1 and the corporate exposure data from Agent 2 and computes a weighted composite score from 0-100. Weighting formula described in the Risk Score section below.
- `simulate_disruption` — Accepts a scenario definition (e.g., "China export ban on gallium") and re-computes the risk score with the specified country-mineral pair removed from the supply picture. Returns the updated score, the delta from baseline, and which remaining suppliers would absorb demand.
- `generate_mitigation_brief` — Uses Granite to generate a short actionable mitigation plan based on the disruption scenario results. Includes specific recommendations like alternative supplier countries, strategic stockpile suggestions, and material substitution options. Sources its recommendations from the USGS knowledge base.

**Output format:** JSON object containing the company name, list of relevant minerals, array of trade flow objects (for globe rendering), the 10-K risk summary, the composite risk score with component breakdown, and optionally a scenario result with mitigation brief.

### Why Plan-Act for the Orchestrator

The workflow is predictable and sequential: gather trade data, gather corporate data, score, optionally simulate. Plan-Act fits because the orchestrator knows the steps upfront and doesn't need exploratory reasoning. The sub-agents use ReAct because they may need to iterate (e.g., trying different search queries on EDGAR, or checking multiple minerals against the trade data).

---

## Data Sources — Verified and Validated

### Source 1: USITC DataWeb (Trade Flow Data)

- **URL:** https://dataweb.usitc.gov
- **What it provides:** U.S. import volumes by HTS commodity code, broken down by source country, with monthly and annual granularity. Includes import value in USD and quantity in kg.
- **Authentication:** Most queries can be performed without logging in. The API requires a Login.gov account with MFA and a bearer token.
- **Format:** CSV download from the web interface, or JSON via the API.

**Hackathon strategy: PRE-DOWNLOAD CSVs.** Do not attempt to use the API live. The Login.gov account setup and the complex JSON query format will waste time during the hackathon. Instead, before the hackathon, go to dataweb.usitc.gov, manually run import queries for each target mineral with all countries selected, and download the results as CSV files. Store these in a /data directory in the project.

**HTS codes to pre-download (VERIFY THESE ON THE LIVE SITE BEFORE THE HACKATHON — codes get reclassified):**

- Gallium: 2804.80 (unwrought gallium — previously classified under 2805.40)
- Germanium: 8112.99 (unwrought germanium and articles thereof)
- Tungsten: 8101 (tungsten ores, concentrates, powders, bars)
- Cobalt: 8105 (cobalt ores, mattes, intermediates)
- Rare earths: 2846 (compounds of rare earth metals)

**Query parameters to use:** Trade type = U.S. Imports for Consumption, Classification = HTS, Time range = 2020-2025, Countries = All countries individually (not aggregated), Output = CSV with quantity and value columns.

**Expected CSV structure:**

| Year | Month | Country | HTS_Code | Commodity_Description | Import_Value_USD | Import_Quantity_KG |
|------|-------|---------|----------|----------------------|-----------------|-------------------|
| 2024 | 12 | China | 2804.80 | Gallium unwrought | 48500000 | 51200 |
| 2024 | 12 | Canada | 2804.80 | Gallium unwrought | 890000 | 520 |

### Source 2: SEC EDGAR Full-Text Search (Corporate Filing Data)

- **URL:** https://efts.sec.gov/LATEST/search-index
- **What it provides:** Full-text search across all EDGAR filings since 2001. Returns filing metadata (accession number, company name, filing date, form type) and URLs to the full filing documents.
- **Authentication:** NONE. This is a free, public, no-auth API run by the SEC.
- **Format:** JSON response from GET requests.

**Hackathon strategy: USE LIVE.** This is the one data source that should be queried in real-time during the demo. It is fast, free, and makes the demo more impressive.

**How to query it:** Send a GET request with query parameters:

- `q` = search terms (e.g., "gallium arsenide" or "rare earth supply")
- `forms` = form type filter (e.g., "10-K")
- `dateRange` = "custom" with `startdt` and `enddt` parameters
- Optionally filter by company CIK number

The response returns an array of filing objects with URLs to the actual HTML filing documents on sec.gov/Archives/. The agent then fetches the filing HTML and uses Granite to find and extract the relevant paragraphs.

**Additionally, for structured company data:** The SEC provides a RESTful API at data.sec.gov that returns company submission history as JSON with no authentication required. Use this to look up CIK numbers and recent filings: https://data.sec.gov/submissions/CIK{10-digit-cik}.json

**Pre-stage for hackathon:** Build a small lookup table mapping demo company names to their CIK numbers:

- NVIDIA: 1045810
- Intel: 50863
- TSMC: 1046179
- Texas Instruments: 97476
- Qualcomm: 804328

### Source 3: USGS Mineral Commodity Summaries (Mineral Reference Data)

- **URL:** https://pubs.usgs.gov/publication/mcs2026
- **What it provides:** Two-page factsheets for 90+ minerals covering world production by country, U.S. import reliance percentage, substitutability assessments, price trends, strategic reserves, and government programs. The 2026 edition (covering 2025 data) is already published.
- **Authentication:** NONE. Fully public, free PDF downloads.
- **Format:** PDF (full report and individual mineral pages), plus CSV data tables.

**Hackathon strategy: DOWNLOAD BEFORE THE HACKATHON AND UPLOAD AS ADK KNOWLEDGE BASE.** Download the individual mineral PDFs for the five target minerals from URLs like https://pubs.usgs.gov/periodicals/mcs2026/mcs2026-gallium.pdf. Upload these into the watsonx Orchestrate ADK as a knowledge base. This gives agents RAG access to answer questions about substitutability, world production leaders, and import reliance without needing to parse PDFs at runtime.

**Also download the CSV data tables** from the USGS Science Data Catalog. These contain structured tabular data (production by country, year-over-year changes) that can be loaded directly by Python tools.

---

## The Data Connection Logic (How the App "Knows" Things)

No single data source tells you "NVIDIA has high gallium exposure AND gallium is 98% sourced from China." The agents connect three independent signals:

**Signal 1 — Industry-level mineral dependency (USGS):** The USGS data tells us which minerals are critical for semiconductor manufacturing. This is the baseline knowledge that gallium, germanium, tungsten, etc. matter for this industry.

**Signal 2 — Country-level trade concentration (USITC):** The trade data tells us where the US gets each mineral. This is country-level, not company-level. It answers "98% of US gallium imports come from China" regardless of which company we are analyzing.

**Signal 3 — Company-level risk disclosure (SEC EDGAR):** The 10-K filings tell us whether a specific company mentions these minerals in their risk factors or supply chain disclosures. This is the company-specific signal. If NVIDIA's 10-K mentions "gallium arsenide substrates" in their risk factors section, that is evidence of dependency.

**What the agents infer:** The composite risk score combines these three signals. A company gets a high score when: (a) the minerals it depends on are highly concentrated in one source country, (b) the company explicitly acknowledges this dependency in its filings, and (c) the USGS data indicates low substitutability.

**Important caveat to acknowledge to judges:** The application does not know the exact tonnage of gallium that NVIDIA purchases. That data is proprietary. The system uses public disclosure signals as a proxy for direct procurement data. This is how real supply chain intelligence firms operate, and it is a valid approach, but it should be stated honestly.

---

## Risk Score Formula

The composite risk score is a number from 0-100 computed as a weighted combination of three components:

### Trade Concentration (40% weight)

Based on the Herfindahl-Hirschman Index (HHI) of country-of-origin concentration for each mineral the company depends on.

- HHI = sum of (country_share ^ 2) for all source countries
- Range: 0 to 1 (1.0 = single source)
- If a company depends on multiple minerals, take the weighted average HHI across all relevant minerals, weighted by the mineral's strategic importance from USGS data

### Corporate Exposure (35% weight)

Based on how prominently the company discloses mineral supply risks in its SEC filings.

- Count the number of 10-K filings (out of recent 3-5 years) that mention critical minerals
- Weight mentions in "Risk Factors" section higher than mentions in general discussion
- Normalize to 0-1 range based on mention frequency and section severity
- A company that mentions "gallium" in risk factors scores higher than one that mentions it in a general industry overview

### Substitutability Risk (25% weight)

Based on USGS assessments of whether alternative materials exist for semiconductor applications.

- Derived from USGS Mineral Commodity Summaries text on each mineral
- Gallium in III-V semiconductors: low substitutability (score ~0.8)
- Tungsten in certain applications: moderate substitutability (score ~0.5)
- Normalize to 0-1 range

### Composite Calculation

composite_score = round((trade_concentration * 0.40 + corporate_exposure * 0.35 + substitutability_risk * 0.25) * 100)

### Scenario Re-scoring

When a disruption scenario is triggered (e.g., "China export ban on gallium"):

1. Remove the banned country from the trade data for the specified mineral
2. Recalculate the HHI on remaining countries (concentration may increase or decrease depending on how remaining supply is distributed)
3. Increase the corporate exposure component by a fixed uplift factor (0.15) to reflect heightened risk
4. Recalculate the composite score
5. Return the delta (new score minus baseline score)

---

## Frontend Architecture

### Technology Stack

- React (functional components with hooks)
- react-globe.gl (3D globe visualization, built on Three.js)
- Tailwind CSS (utility styling)
- react-countup or requestAnimationFrame (score animation)
- Natural Earth 110m GeoJSON (country polygon data, free)
- NASA Blue Marble or Earth Night texture (globe background)

### Layout: Three-Panel Design

The interface is a three-column layout optimized for projector demos:

**Left Panel (~200px, fixed width):**

- Company selector dropdown (pre-populated with 4-5 demo companies)
- Mineral filter checkboxes (gallium, germanium, tungsten, cobalt, rare earths — all checked by default)
- Scenario simulation buttons ("Simulate: China Gallium Ban", "Simulate: China Germanium Ban", "Simulate: Russia Cobalt Ban")
- Compare button to add a second company for side-by-side analysis (stretch goal)

**Center Panel (flex, takes remaining space):**

- 3D interactive globe (react-globe.gl)
- Globe slowly auto-rotates on load, stops when user interacts
- Trade flow arcs rendered on the globe surface
- Country polygons highlighted by risk level
- Globe camera auto-focuses on the dominant trade route when arcs load

**Right Panel (~320px, fixed width):**

- Risk score card with animated counter (0-100)
- Score breakdown bars showing the three components (trade concentration, corporate exposure, substitutability)
- 10-K finding summary (Granite-generated text from the corporate exposure agent)
- Agent activity feed showing real-time status of each agent's work
- Mitigation brief panel (appears after scenario simulation, slides in from bottom)

### Globe Visualization Details

**Arc rendering:** Each arc represents a trade flow from a mineral-producing country to the United States. The arc properties encode data:

- **Thickness (stroke):** Proportional to that country's share of US imports for the mineral. A country supplying 98% of imports has a visually dominant thick arc. A country supplying 1% has a barely visible thin arc.
- **Color:** Encodes risk level. Red (#ef4444) for critical concentration (share > 50%), Amber (#f59e0b) for elevated (share > 20%), Green (#22c55e) for low concentration.
- **Animation:** Arcs use dash animation to create a "flowing" effect from source country toward the US. The dominant arc flows faster, reinforcing the visual weight.

**Arc data structure:** Each arc object contains: startLat, startLng (source country centroid), endLat, endLng (Washington DC as US anchor point), mineral name, volume in kg, percentage share, risk level string, and stroke width.

**Country highlighting:** Country polygons from Natural Earth GeoJSON are colored by their aggregate risk contribution. China glows red if it dominates multiple minerals. Polygons can be raised slightly off the globe surface (polygonAltitude) for high-risk countries, creating a subtle 3D emphasis.

**Country coordinate mapping:** A pre-built JSON file maps country names to their geographic centroid lat/lng. This is a static lookup — only need coordinates for the ~30 countries that appear in USITC mineral import data.

### Globe Texture

Use the NASA Earth Night texture (dark globe) rather than the Blue Marble (bright blue). The dark background makes colored arcs and country highlights pop dramatically on a projector screen. The arcs become glowing colored rivers on a dark surface, which is much more visually striking.

### UX State Machine

**State: Empty (app load)**

- Globe auto-rotates slowly
- Left panel shows company dropdown with placeholder text "Select a company"
- Right panel shows placeholder: "Select a company to begin analysis"
- No arcs, no country highlights

**State: Loading (company selected)**

- Right panel: Agent activity feed begins streaming agent status messages
- Globe: No arcs yet, continues rotating
- Agent messages appear one by one with slight delays to show progression
- Example messages: "Risk Orchestrator: Initiating analysis...", "Trade Intel Agent: Processing gallium import data...", "Corporate Exposure Agent: Searching NVIDIA 10-K filings..."

**State: Results (agents complete)**

- Globe: Arcs fade in one mineral at a time, camera auto-pans to center on the dominant trade route
- Right panel: Score counter animates from 0 to the final score, breakdown bars fill in, 10-K summary text appears
- Left panel: Mineral checkboxes update to show which minerals were found relevant
- Transition takes approximately 1-2 seconds for visual impact

**State: Scenario Active (disruption simulated)**

- Globe: The disrupted arc (e.g., China gallium) fades to a ghost (low opacity, stops flowing). A pulsing red overlay appears on the disrupted country. Remaining arcs for that mineral swell and change to amber.
- Right panel: Score counter animates from baseline to new score. Mitigation brief panel slides in below the score card with Granite-generated recommendations.
- Transition takes approximately 2 seconds — this is the demo's climax moment

**State: Comparison (stretch goal)**

- Globe shows arcs for two companies simultaneously, differentiated by mineral or color scheme
- Right panel splits into two score cards side by side
- Demonstrates that different companies have different exposure profiles

### Frontend-to-Backend Communication

The React frontend communicates with the watsonx Orchestrate Developer Edition running locally at localhost:4321. The frontend sends natural language queries to the ADK's chat endpoint, and the orchestrator agent processes them.

The orchestrator agent's instructions specify that it must return results as structured JSON with a defined schema (company, minerals, trade_flows array, filing_summary, risk_score object). The frontend parses this JSON and maps it to globe arc data and score card data.

**Fallback plan:** If the live ADK integration is unreliable under hackathon time pressure, pre-compute results for 4-5 demo companies, store as static JSON files, and have the frontend load them with a simulated agent activity feed (timed message reveals). The agent logic should still work in a terminal demo to prove the architecture. Judges care about the architecture and demo experience — if agents work correctly in CLI and the frontend tells the right visual story, the project succeeds.

### Color System

Maintain consistent color language across all UI elements:

- Critical risk: Red (#ef4444) — arcs with >50% share, high-risk countries, danger indicators
- Elevated risk: Amber (#f59e0b) — moderate concentration, stressed suppliers in scenario mode
- Low risk: Green (#22c55e) — diversified supply, low concentration
- Disrupted: Ghost red (rgba(239, 68, 68, 0.2)) — faded arcs for banned trade routes
- Neutral: Slate/gray for UI chrome, text, borders

Use this palette on arcs, country highlights, score card indicators, breakdown bars, and scenario buttons. A judge should be able to glance at the screen and understand the risk picture without reading text.

---

## Observability

Enable Langfuse integration via the ADK for full agent execution tracing. Start the developer edition with: `orchestrate server start -e .env -l`

This provides:

- End-to-end traces of every agent execution showing the orchestrator dispatching to sub-agents
- Individual LLM call traces showing Granite's input prompts and output responses
- Tool call traces showing which Python functions were invoked with what arguments
- Latency metrics for each step
- Token usage per LLM call

During the demo, the Langfuse dashboard (localhost) can be shown briefly to demonstrate the audit trail: "Here's exactly how the agents reasoned through this risk assessment — every step is traceable." This matters for the governance angle and differentiates from a black-box approach.

---

## Project File Structure

```
mineralwatch/
├── .env                          # IBM Cloud API key, entitlement key, watsonx config
├── data/
│   ├── usitc/
│   │   ├── gallium_imports.csv   # Pre-downloaded from USITC DataWeb
│   │   ├── germanium_imports.csv
│   │   ├── tungsten_imports.csv
│   │   ├── cobalt_imports.csv
│   │   └── rare_earths_imports.csv
│   ├── usgs/
│   │   ├── mcs2026-gallium.pdf   # Individual mineral summaries
│   │   ├── mcs2026-germanium.pdf
│   │   ├── mcs2026-tungsten.pdf
│   │   ├── mcs2026-cobalt.pdf
│   │   └── mcs2026-rare-earths.pdf
│   └── reference/
│       ├── country_coords.json    # Country name → lat/lng centroid mapping
│       └── company_ciks.json      # Company name → SEC CIK number mapping
├── agents/
│   ├── trade_intel_agent.yaml     # Agent spec for trade intelligence
│   ├── corporate_exposure_agent.yaml
│   └── risk_orchestrator.yaml     # Orchestrator with collaborators defined
├── tools/
│   ├── query_import_volumes.py    # Reads USITC CSVs, returns trade flows
│   ├── compute_herfindahl.py      # HHI concentration calculation
│   ├── get_mineral_profile.py     # RAG query against USGS knowledge base
│   ├── search_edgar_10k.py        # Hits efts.sec.gov live API
│   ├── extract_mineral_deps.py    # Granite NER on filing text
│   ├── summarize_risk_section.py  # Granite summarization
│   ├── compute_composite_risk.py  # Weighted risk score formula
│   ├── simulate_disruption.py     # Scenario re-scoring logic
│   └── generate_mitigation.py     # Granite mitigation brief generation
├── knowledge/
│   └── usgs_minerals/             # PDFs uploaded as ADK knowledge base
├── frontend/
│   ├── package.json
│   ├── tailwind.config.js
│   ├── public/
│   │   └── earth-night.jpg        # NASA dark globe texture
│   └── src/
│       ├── App.jsx                # Three-panel layout container
│       ├── components/
│       │   ├── Globe.jsx          # react-globe.gl wrapper with arc rendering
│       │   ├── CompanySelector.jsx
│       │   ├── MineralFilters.jsx
│       │   ├── RiskScoreCard.jsx  # Animated score + breakdown bars
│       │   ├── FilingSummary.jsx  # 10-K finding display
│       │   ├── AgentFeed.jsx      # Real-time agent activity stream
│       │   ├── ScenarioControls.jsx
│       │   └── MitigationBrief.jsx
│       ├── hooks/
│       │   ├── useAgentQuery.js   # Manages ADK chat endpoint communication
│       │   └── useGlobeData.js    # Transforms agent JSON output → arc objects
│       └── data/
│           ├── countryCoords.json # Static country coordinate lookup
│           └── fallbackResults.json # Pre-computed results for demo fallback
└── README.md
```

---

## Pre-Hackathon Checklist

These tasks should be completed before the hackathon starts to avoid wasting build time on data wrangling:

1. **USITC Data:** Go to dataweb.usitc.gov, run import queries for each of the 5 target minerals with all countries, download CSVs, verify they contain country, quantity, and value columns
2. **USGS PDFs:** Download individual mineral summaries from pubs.usgs.gov for gallium, germanium, tungsten, cobalt, and rare earths (2026 edition)
3. **USGS CSVs:** Download the structured data tables from the USGS Science Data Catalog for the same minerals
4. **EDGAR Test:** Send a test GET request to efts.sec.gov/LATEST/search-index with a query like q="gallium"&forms=10-K to confirm the endpoint works and understand the JSON response format
5. **CIK Lookup:** Confirm CIK numbers for demo companies (NVIDIA, Intel, TSMC, Texas Instruments, Qualcomm) via data.sec.gov
6. **Country Coordinates:** Build the country_coords.json mapping for the ~30 countries that appear in USITC mineral trade data
7. **IBM Cloud Account:** Set up the IBM Cloud account, get API keys, get the watsonx Orchestrate entitlement key
8. **ADK Installation:** Install the watsonx Orchestrate ADK (pip install ibm-watsonx-orchestrate), verify Docker is running, test that `orchestrate server start` works
9. **Globe Texture:** Download the NASA Earth Night texture image
10. **Natural Earth GeoJSON:** Download the 110m country polygons dataset from Natural Earth for globe country highlighting

---

## Demo Script (3 Minutes)

**0:00 — Context (15 seconds)**
"Semiconductor supply chains depend on a handful of critical minerals. China controls 98% of gallium production. No tool maps how this concentration risk compounds across a specific company's supply chain. MineralWatch changes that."

**0:15 — Select Company (30 seconds)**
Select NVIDIA from the dropdown. Point out the agent activity feed as both sub-agents begin working. "Our risk orchestrator dispatches two specialized agents — one analyzing US trade data, one searching NVIDIA's SEC filings."

**0:45 — Results Appear (45 seconds)**
Arcs populate the globe. "See this thick red arc from China? That represents 98% of US gallium imports flowing from a single country. Our corporate exposure agent found that NVIDIA's latest 10-K explicitly identifies gallium arsenide substrate availability as a material risk." Point to the risk score: 82/100. Walk through the three breakdown components briefly.

**1:30 — Scenario Simulation (45 seconds)**
Click "Simulate: China Gallium Export Ban." The arc fades, score jumps to 96. "Watch — when we simulate a Chinese export ban, that trade route disappears. The remaining suppliers from Canada and Germany are stressed. Our AI generates specific mitigation recommendations: diversify to Canadian suppliers, increase strategic stockpile, evaluate GaN-on-Si alternatives."

**2:15 — Architecture (30 seconds)**
Briefly show the Langfuse trace. "Every agent decision is fully traceable. Three agents, each with specialized tools, orchestrated through IBM watsonx Orchestrate. The system uses Granite 3.3 for NLP extraction and summarization. All data sources are public US government data."

**2:45 — Close (15 seconds)**
"MineralWatch turns public data into actionable intelligence. It helps semiconductor companies prepare for supply chain disruptions before they happen, not after."

---

## Key Technical Decisions and Rationale

**Why pre-download USITC data instead of using the API live:** The USITC API requires Login.gov MFA setup and uses a complex JSON query format. During a 48-hour hackathon, this setup could take an hour and introduce fragile auth dependencies. Pre-downloaded CSVs are reliable, fast, and contain identical data.

**Why hit EDGAR live instead of pre-downloading:** EDGAR's full-text search API is free, fast, and requires no authentication. Live queries make the demo more impressive and prove the system works with any company, not just pre-staged ones.

**Why Granite 3.3 8B instead of a larger model:** This is an IBM hackathon — using IBM's own model family is expected and appreciated. The 8B parameter size is sufficient for NER extraction, summarization, and recommendation generation. It is also fast enough for a live demo without noticeable latency.

**Why Plan-Act for the orchestrator and ReAct for sub-agents:** The orchestrator's workflow is predictable (gather trade data → gather corporate data → score → optionally simulate), making Plan-Act appropriate. The sub-agents may need to iterate (try different EDGAR search queries, check multiple minerals) making ReAct's explore-observe-act loop more flexible.

**Why react-globe.gl instead of a 2D map:** The 3D globe with animated arcs is the visual differentiator. It communicates geographic concentration risk instantly and creates a memorable demo moment. react-globe.gl handles WebGL rendering with a React-friendly API and can render 50+ arcs without performance issues.

**Why Earth Night texture instead of Blue Marble:** The dark globe makes colored arcs and country highlights dramatically more visible, especially on a projector in a hackathon presentation room. Glowing colored arcs on a dark surface have significantly more visual impact than the same arcs on a bright blue background.

**Why Langfuse over watsonx.governance:** Langfuse provides immediate, visual observability traces that can be shown in a demo. watsonx.governance is a heavier enterprise product that requires more setup and is harder to demo in 3 minutes. Langfuse integration is built into the ADK with a single CLI flag.