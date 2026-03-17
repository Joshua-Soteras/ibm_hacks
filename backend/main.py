from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import json
import time
import os

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

IBM_API_KEY = os.getenv("IBM_API_KEY")



@app.get("/")
def root():
    return {"message": f"Hello, World!"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/companies")
def get_companies():
    from analytics import get_company_list
    return {"companies": get_company_list()}


@app.get("/analyze/{company}")
def analyze(company: str):
    from analytics import analyze_company
    result = analyze_company(company)
    if result is None:
        return {"error": "Company not found"}, 404
    return result


# --- ACENT-READY ENDPOINTS (Skills) ---

@app.get("/api/minerals/list")
def list_minerals():
    from analytics import get_all_minerals
    return {"minerals": get_all_minerals()}


@app.get("/api/company/minerals/{company}")
def company_minerals(company: str):
    from analytics import get_company_minerals
    return {"company": company, "minerals": get_company_minerals(company)}


@app.get("/api/mineral/risk/{mineral}")
def mineral_risk(mineral: str):
    from analytics import get_mineral_risk
    return get_mineral_risk(mineral)


@app.get("/api/company/summary/{company}")
def company_summary(company: str):
    from analytics import analyze_company
    result = analyze_company(company)
    if result:
        return {"company": company, "summary": result['summary']}
    return {"error": "Company not found"}, 404


# --- SCENARIO & SIMULATION ENDPOINTS ---

@app.get("/api/company/scenarios/{company}")
def company_scenarios(company: str):
    from analytics import get_company_scenarios
    scenarios = get_company_scenarios(company)
    return {"company": company, "scenarios": scenarios}


# --- ADK TOOL CALLBACK ENDPOINTS ---

@app.get("/api/mineral/trade/{mineral}")
def mineral_trade_flows(mineral: str, year: int = None):
    from analytics import get_mineral_trade_flows
    return get_mineral_trade_flows(mineral, year)


@app.get("/api/mineral/profile/{mineral}")
def mineral_profile(mineral: str):
    from analytics import get_mineral_profile_data
    return get_mineral_profile_data(mineral)


@app.get("/api/company/dependencies/{company}")
def company_dependencies(company: str):
    from analytics import get_company_dependencies
    return get_company_dependencies(company)


@app.get("/api/risk-summary")
def risk_summary(company: str, mineral: str = None):
    from analytics import get_risk_summary
    return get_risk_summary(company, mineral)


@app.get("/api/edgar/cik/{company}")
def edgar_cik(company: str):
    from analytics import lookup_edgar_cik
    return lookup_edgar_cik(company)


class SimulateRequest(BaseModel):
    company: str
    country: str
    mineral: str
    disruption_pct: float = 100.0


@app.post("/api/simulate")
def simulate(req: SimulateRequest):
    from analytics import simulate_company_disruption
    result = simulate_company_disruption(req.company, req.country, req.mineral, req.disruption_pct)
    if result is None:
        return {"error": "Company not found"}, 404
    return result


# --- SSE STREAMING ENDPOINT ---

def _mock_analysis_generator(company: str):
    """Local-only analysis stream (fallback when agent credentials are not configured)."""
    def emit(data: dict):
        return f"data: {json.dumps(data)}\n\n"

    from analytics import get_db_conn, _get_trade_data_for_company, _get_corporate_data_for_company
    import pandas as pd

    yield emit({"stage": "orchestrator_planning", "title": "Risk Orchestrator", "status": "active",
                 "trace": f"> Planning analysis for {company}\n> Identifying mineral dependencies..."})
    time.sleep(0.3)

    try:
        conn = get_db_conn()
        query_filings = "SELECT * FROM edgar_filing_details WHERE Company LIKE ?"
        company_filings = pd.read_sql_query(query_filings, conn, params=(f"%{company}%",))

        if company_filings.empty:
            yield emit({"stage": "complete", "result": None})
            conn.close()
            return

        minerals = company_filings['Mineral'].unique().tolist()

        yield emit({"stage": "orchestrator_planning", "title": "Risk Orchestrator", "status": "completed",
                     "trace": f"> Found {len(minerals)} mineral dependencies\n> Dispatching sub-agents..."})
        time.sleep(0.2)

        yield emit({"stage": "trade_intel", "title": "Trade Intelligence Agent", "status": "active",
                     "trace": f"> Querying trade flows for {len(minerals)} minerals\n> Computing HHI concentration indices..."})
        time.sleep(0.3)

        trade_data = _get_trade_data_for_company(company, conn, minerals)

        yield emit({"stage": "trade_intel", "title": "Trade Intelligence Agent", "status": "completed",
                     "trace": f"> Analyzed {len(trade_data['flows'])} trade routes\n> Computed {len(trade_data['hhis'])} HHI scores\n> Trade risk score: {round(trade_data['trade_score'])}"})
        time.sleep(0.2)

        yield emit({"stage": "corporate_exposure", "title": "Corporate Exposure Agent", "status": "active",
                     "trace": f"> Scanning USGS supply risk data\n> Cross-referencing SEC filings..."})
        time.sleep(0.3)

        corp_data = _get_corporate_data_for_company(conn, minerals)

        yield emit({"stage": "corporate_exposure", "title": "Corporate Exposure Agent", "status": "completed",
                     "trace": f"> Corporate exposure score: {corp_data['corporate_score']}\n> Substitutability risk: {corp_data['subst_score']}"})
        time.sleep(0.2)

        yield emit({"stage": "orchestrator_scoring", "title": "Risk Orchestrator — Scoring", "status": "active",
                     "trace": "> Computing weighted composite score\n> Weights: trade 40%, corporate 35%, substitutability 25%"})
        time.sleep(0.2)

        trade_score = trade_data["trade_score"]
        corporate_score = corp_data["corporate_score"]
        subst_score = corp_data["subst_score"]
        composite_score = round(trade_score * 0.40 + corporate_score * 0.35 + subst_score * 0.25)

        summary = company_filings['Snippet'].iloc[0] if 'Snippet' in company_filings.columns else "No specific filing snippets found."

        result = {
            "company": company,
            "score": composite_score,
            "breakdown": {
                "trade": round(trade_score),
                "corporate": round(corporate_score),
                "substitutability": round(subst_score)
            },
            "minerals": minerals,
            "trade_flows": trade_data["flows"],
            "summary": summary
        }

        yield emit({"stage": "orchestrator_scoring", "title": "Risk Orchestrator — Scoring", "status": "completed",
                     "trace": f"> Composite risk score: {composite_score}\n> Analysis complete for {company}"})
        time.sleep(0.1)

        yield emit({"stage": "complete", "result": result})
        conn.close()

    except Exception as e:
        yield emit({"stage": "error", "error": str(e)})


@app.get("/api/analyze-stream/{company}")
def analyze_stream(company: str):
    if os.getenv("ORCHESTRATE_URL") and os.getenv("IBM_API_KEY"):
        from agent_client import run_analysis_agent_generator
        return StreamingResponse(
            run_analysis_agent_generator(company),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    return StreamingResponse(
        _mock_analysis_generator(company),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/custom-scenario-stream/{company}")
def custom_scenario_stream(company: str, scenario: str):
    from agent_client import run_custom_scenario_generator
    return StreamingResponse(
        run_custom_scenario_generator(company, scenario),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


@app.get("/api/agent-diagnostics")
def agent_diagnostics():
    """Diagnostic endpoint for debugging cloud agent connectivity."""
    diag = {
        "orchestrate_url_set": bool(os.getenv("ORCHESTRATE_URL")),
        "ibm_api_key_set": bool(os.getenv("IBM_API_KEY")),
        "backend_api_url_set": bool(os.getenv("BACKEND_API_URL")),
        "backend_api_url": os.getenv("BACKEND_API_URL", ""),
        "agents": {},
        "callback_reachable": None,
    }

    # Test agent UUID resolution
    if diag["orchestrate_url_set"] and diag["ibm_api_key_set"]:
        try:
            from agent_client import _get_authenticator, _resolve_agent_uuid
            authenticator = _get_authenticator()
            for name in ["risk_orchestrator", "trade_intel_agent", "corporate_exposure_agent"]:
                try:
                    uuid = _resolve_agent_uuid(name, authenticator)
                    diag["agents"][name] = {"status": "resolved", "uuid": uuid}
                except Exception as e:
                    diag["agents"][name] = {"status": "error", "error": str(e)}
        except Exception as e:
            diag["agents"]["_auth"] = {"status": "error", "error": str(e)}

    # Test callback reachability
    backend_url = os.getenv("BACKEND_API_URL", "")
    if backend_url:
        try:
            import requests as http_requests
            r = http_requests.get(f"{backend_url}/health", timeout=5,
                                  headers={"ngrok-skip-browser-warning": "true"})
            diag["callback_reachable"] = r.status_code == 200
        except Exception as e:
            diag["callback_reachable"] = False
            diag["callback_error"] = str(e)

    return diag


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)