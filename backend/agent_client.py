"""
Agent client for invoking the risk_orchestrator via IBM Watson Orchestrate RunClient.
Uses IAMAuthenticator for auth and polling for run completion.
Falls back to keyword-based extraction + simulate_company_disruption() if the agent is unavailable.
"""

import json
import os
import time
import logging
import requests as http_requests

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

ORCHESTRATE_URL = os.getenv("ORCHESTRATE_URL", "")
IBM_API_KEY = os.getenv("IBM_API_KEY", "")

# Cache agent UUID resolution
_agent_uuid_cache: dict = {}


def _emit(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


def _get_authenticator():
    """Create IAMAuthenticator from IBM_API_KEY."""
    from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
    return IAMAuthenticator(apikey=IBM_API_KEY)


def _resolve_agent_uuid(agent_name: str, authenticator) -> str:
    """Resolve agent name to UUID via the Orchestrate agents API."""
    if agent_name in _agent_uuid_cache:
        return _agent_uuid_cache[agent_name]

    token = authenticator.token_manager.get_token()
    headers = {"Authorization": f"Bearer {token}"}
    r = http_requests.get(
        f"{ORCHESTRATE_URL}/v1/orchestrate/agents",
        headers=headers,
        timeout=15,
    )
    if r.status_code == 200:
        agents = r.json() if isinstance(r.json(), list) else r.json().get("agents", [])
        for agent in agents:
            _agent_uuid_cache[agent.get("name", "")] = agent.get("id", "")
        if agent_name in _agent_uuid_cache:
            return _agent_uuid_cache[agent_name]

    raise ValueError(f"Agent '{agent_name}' not found in deployed agents")


def _get_known_countries_and_minerals():
    """Load known country and mineral names from DB for keyword matching."""
    try:
        from analytics import get_db_conn
        import pandas as pd
        conn = get_db_conn()
        countries = pd.read_sql_query("SELECT DISTINCT Country FROM trade_data", conn)["Country"].tolist()
        minerals = pd.read_sql_query("SELECT DISTINCT Mineral FROM edgar_filing_details", conn)["Mineral"].tolist()
        conn.close()
        return countries, minerals
    except Exception:
        return [], []


def _extract_country_mineral(scenario_text: str, countries: list, minerals: list):
    """Case-insensitive keyword extraction of country and mineral from scenario text."""
    text_lower = scenario_text.lower()
    matched_country = None
    matched_mineral = None

    for c in sorted(countries, key=len, reverse=True):
        if c.lower() in text_lower:
            matched_country = c
            break

    for m in sorted(minerals, key=len, reverse=True):
        if m.lower() in text_lower:
            matched_mineral = m
            break

    return matched_country, matched_mineral


def _try_agent_stream(company: str, scenario_text: str):
    """
    Invoke risk_orchestrator via RunClient with polling.
    The agent's analysis is shown in the AgentWorkflow panel.
    A local simulation generates the structured SimulationResult for MetricsPanel/GlobeView.
    """
    from ibm_watsonx_orchestrate.client.chat import RunClient

    authenticator = _get_authenticator()
    agent_uuid = _resolve_agent_uuid("risk_orchestrator", authenticator)

    run_client = RunClient(
        base_url=ORCHESTRATE_URL,
        authenticator=authenticator,
        is_local=False,
    )

    prompt = (
        f"Assess the supply chain risk impact on {company} for the following scenario: "
        f"'{scenario_text}'. "
        f"Use your tools to analyze trade concentration, corporate exposure, and substitutability risk. "
        f"If specific countries and minerals are mentioned, run simulate_disruption to model the impact. "
        f"Provide a clear risk assessment with scores and recommendations."
    )

    # Stage 1: Dispatch to agent
    yield _emit({
        "stage": "agent_reasoning",
        "title": "Risk Orchestrator — Analyzing",
        "status": "active",
        "trace": f"> Dispatching to deployed risk orchestrator agent...\n> Scenario: \"{scenario_text}\"",
    })

    try:
        resp = run_client.create_run(message=prompt, agent_id=agent_uuid)
    except Exception as e:
        logger.error(f"create_run failed: {e}")
        raise

    run_id = resp.get("run_id", "")
    thread_id = resp.get("thread_id", "")

    yield _emit({
        "stage": "agent_reasoning",
        "title": "Risk Orchestrator — Analyzing",
        "status": "active",
        "trace": f"> Run created (id: {run_id[:8]}...)\n> Agent is processing with sub-agents...",
    })

    # Stage 2: Poll for completion
    max_polls = 90  # 3 minutes at 2s intervals
    poll_messages = [
        "Querying trade intelligence data...",
        "Analyzing corporate exposure via SEC filings...",
        "Computing concentration indices (HHI)...",
        "Evaluating substitutability risk...",
        "Running disruption simulation...",
        "Synthesizing composite risk scores...",
    ]

    for i in range(max_polls):
        time.sleep(2)
        try:
            status = run_client.get_run_status(run_id)
        except Exception as e:
            logger.warning(f"Poll error: {e}")
            continue

        run_state = status.get("status", "").lower()

        if run_state == "completed":
            # Extract response text
            result_data = status.get("result", {}).get("data", {})
            message = result_data.get("message", {})
            content_list = message.get("content", [])
            agent_text = ""
            for c in content_list:
                if isinstance(c, dict) and "text" in c:
                    agent_text = c["text"]
                    break
                elif isinstance(c, str):
                    agent_text = c
                    break

            # Truncate for display
            display_text = agent_text[:600] + ("..." if len(agent_text) > 600 else "")

            yield _emit({
                "stage": "agent_reasoning",
                "title": "Risk Orchestrator — Analysis Complete",
                "status": "completed",
                "trace": f"> Agent analysis complete\n> {display_text}",
            })

            # Now run local simulation for structured SimulationResult
            yield _emit({
                "stage": "agent_response",
                "title": "Risk Orchestrator — Simulating",
                "status": "active",
                "trace": "> Generating structured disruption model...",
            })

            countries, minerals = _get_known_countries_and_minerals()
            matched_country, matched_mineral = _extract_country_mineral(scenario_text, countries, minerals)

            # Also try to extract from agent response if prompt didn't have explicit matches
            if not matched_country or not matched_mineral:
                full_text = scenario_text + " " + agent_text
                c2, m2 = _extract_country_mineral(full_text, countries, minerals)
                matched_country = matched_country or c2
                matched_mineral = matched_mineral or m2

            # Fill in missing side from trade flows
            if not matched_mineral or not matched_country:
                from analytics import analyze_company
                baseline = analyze_company(company)
                if baseline:
                    for flow in baseline["trade_flows"]:
                        if matched_mineral and not matched_country and flow["mineral"].lower() == matched_mineral.lower() and flow["share"] > 20:
                            matched_country = flow["country"]
                            break
                        if matched_country and not matched_mineral and flow["country"].lower() == matched_country.lower() and flow["share"] > 20:
                            matched_mineral = flow["mineral"]
                            break

            if matched_country and matched_mineral:
                from analytics import simulate_company_disruption
                sim_result = simulate_company_disruption(company, matched_country, matched_mineral, 75.0)

                if sim_result:
                    yield _emit({
                        "stage": "agent_response",
                        "title": "Risk Orchestrator — Response",
                        "status": "completed",
                        "trace": f"> Simulation: {matched_country} × {matched_mineral}\n> Baseline: {sim_result['baseline_score']} → Disrupted: {sim_result['disrupted_score']} (Δ{sim_result['score_delta']:+d})\n> Severity: {sim_result['severity']}",
                    })
                    time.sleep(0.1)
                    yield _emit({"stage": "complete", "result": sim_result})
                    return

            # No simulation possible, but agent analysis was shown
            yield _emit({
                "stage": "agent_response",
                "title": "Risk Orchestrator — Response",
                "status": "completed",
                "trace": "> Agent analysis displayed above.\n> Could not extract country/mineral pair for structured simulation.\n> Tip: mention a specific country and mineral.",
            })
            yield _emit({"stage": "complete", "result": None})
            return

        elif run_state in ("failed", "cancelled"):
            error_msg = status.get("last_error", {})
            yield _emit({"stage": "error", "error": f"Agent run {run_state}: {error_msg}"})
            return

        # Yield progress updates
        if i < len(poll_messages):
            msg = poll_messages[i]
        elif i % 3 == 0:
            msg = f"Still processing... ({i * 2}s elapsed)"
        else:
            continue  # Don't flood with updates

        yield _emit({
            "stage": "agent_reasoning",
            "title": "Risk Orchestrator — Analyzing",
            "status": "active",
            "trace": f"> {msg}",
        })

    yield _emit({"stage": "error", "error": "Agent timed out after 3 minutes"})


def _fallback_stream(company: str, scenario_text: str):
    """
    Keyword-based fallback: extract country/mineral from text, run simulate_company_disruption().
    """
    yield _emit({
        "stage": "agent_reasoning",
        "title": "Risk Orchestrator — Analyzing",
        "status": "active",
        "trace": f"> Agent unavailable, using keyword analysis...\n> Parsing: \"{scenario_text}\"",
    })
    time.sleep(0.3)

    countries, minerals = _get_known_countries_and_minerals()
    matched_country, matched_mineral = _extract_country_mineral(scenario_text, countries, minerals)

    if not matched_country and not matched_mineral:
        yield _emit({
            "stage": "agent_reasoning",
            "title": "Risk Orchestrator — Analyzing",
            "status": "completed",
            "trace": "> Could not identify a specific country or mineral from scenario text.\n> Try mentioning a country (e.g., China) and mineral (e.g., Gallium).",
        })
        yield _emit({"stage": "error", "error": "No country or mineral could be extracted from the scenario. Please mention specific countries or minerals."})
        return

    trace_parts = ["> Keyword extraction results:"]
    if matched_country:
        trace_parts.append(f">   Country: {matched_country}")
    if matched_mineral:
        trace_parts.append(f">   Mineral: {matched_mineral}")

    yield _emit({
        "stage": "agent_reasoning",
        "title": "Risk Orchestrator — Analyzing",
        "status": "completed",
        "trace": "\n".join(trace_parts),
    })
    time.sleep(0.2)

    yield _emit({
        "stage": "agent_response",
        "title": "Risk Orchestrator — Simulating",
        "status": "active",
        "trace": f"> Running disruption simulation (75% disruption)...\n> {matched_country or 'Any'} × {matched_mineral or 'Any'}",
    })
    time.sleep(0.3)

    from analytics import simulate_company_disruption, analyze_company

    if not matched_mineral or not matched_country:
        baseline = analyze_company(company)
        if baseline:
            for flow in baseline["trade_flows"]:
                if matched_mineral and not matched_country and flow["mineral"].lower() == matched_mineral.lower():
                    if flow["share"] > 20:
                        matched_country = flow["country"]
                        break
                if matched_country and not matched_mineral and flow["country"].lower() == matched_country.lower():
                    if flow["share"] > 20:
                        matched_mineral = flow["mineral"]
                        break

    if not matched_country or not matched_mineral:
        yield _emit({
            "stage": "agent_response",
            "title": "Risk Orchestrator — Response",
            "status": "completed",
            "trace": "> Could not determine both country and mineral for simulation.\n> Provide both in your scenario description.",
        })
        yield _emit({"stage": "error", "error": "Need both a country and mineral to simulate. Try: 'What if China restricts Gallium exports?'"})
        return

    result = simulate_company_disruption(company, matched_country, matched_mineral, 75.0)

    if result:
        yield _emit({
            "stage": "agent_response",
            "title": "Risk Orchestrator — Response",
            "status": "completed",
            "trace": f"> Simulation complete\n> Baseline: {result['baseline_score']} → Disrupted: {result['disrupted_score']} (Δ{result['score_delta']:+d})\n> Severity: {result['severity']}",
        })
        time.sleep(0.1)
        yield _emit({"stage": "complete", "result": result})
    else:
        yield _emit({"stage": "error", "error": f"Simulation failed for {company} / {matched_country} / {matched_mineral}"})


def _run_local_analytics(company: str):
    """Run analyze_company in the calling thread. Returns result dict or None."""
    try:
        from analytics import analyze_company
        return analyze_company(company)
    except Exception as e:
        logger.error(f"Local analytics failed: {e}")
        return None


def _dispatch_agent(company: str):
    """Create RunClient, resolve UUID, dispatch analysis run. Returns (run_client, run_id) or raises."""
    from ibm_watsonx_orchestrate.client.chat import RunClient

    authenticator = _get_authenticator()
    agent_uuid = _resolve_agent_uuid("risk_orchestrator", authenticator)

    run_client = RunClient(
        base_url=ORCHESTRATE_URL,
        authenticator=authenticator,
        is_local=False,
    )

    prompt = (
        f"Perform a comprehensive supply chain risk analysis for {company}. "
        f"Use your tools to: 1) Analyze trade concentration and HHI indices for all minerals {company} depends on, "
        f"2) Assess corporate exposure via SEC filing data, "
        f"3) Evaluate substitutability risk for critical minerals. "
        f"Provide a detailed risk assessment with specific scores, key vulnerabilities, and recommendations."
    )

    resp = run_client.create_run(message=prompt, agent_id=agent_uuid)
    run_id = resp.get("run_id", "")
    return run_client, run_id


def run_analysis_agent_generator(company: str):
    """
    SSE generator for company analysis that runs the real risk_orchestrator agent
    concurrently with local analytics. Emits the same 4 stage IDs the frontend expects.
    Falls back to local-only data if the agent is unavailable.
    """
    from concurrent.futures import ThreadPoolExecutor, Future

    agent_available = True
    agent_completed = False
    agent_text = ""
    agent_future: Future | None = None
    analytics_future: Future | None = None

    # Stage 1: orchestrator_planning — active
    yield _emit({
        "stage": "orchestrator_planning",
        "title": "Risk Orchestrator",
        "status": "active",
        "trace": f"> Planning analysis for {company}\n> Dispatching agent and local analytics concurrently...",
    })

    executor = ThreadPoolExecutor(max_workers=2)
    try:
        analytics_future = executor.submit(_run_local_analytics, company)

        try:
            agent_future = executor.submit(_dispatch_agent, company)
        except Exception as e:
            logger.warning(f"Agent dispatch submit failed: {e}")
            agent_available = False
    except Exception as e:
        logger.error(f"Executor failed: {e}")
        agent_available = False

    # Wait for local analytics (~0.5s)
    local_result = None
    if analytics_future:
        try:
            local_result = analytics_future.result(timeout=30)
        except Exception as e:
            logger.error(f"Local analytics future failed: {e}")

    if local_result is None:
        yield _emit({
            "stage": "orchestrator_planning",
            "title": "Risk Orchestrator",
            "status": "completed",
            "trace": f"> Company '{company}' not found in database",
        })
        yield _emit({"stage": "complete", "result": None})
        executor.shutdown(wait=False)
        return

    minerals = local_result.get("minerals", [])

    # Resolve agent dispatch
    run_client = None
    run_id = None
    if agent_available and agent_future:
        try:
            run_client, run_id = agent_future.result(timeout=30)
        except ImportError:
            logger.warning("ibm_watsonx_orchestrate not installed")
            agent_available = False
        except Exception as e:
            logger.warning(f"Agent dispatch failed: {e}")
            agent_available = False

    executor.shutdown(wait=False)

    agent_note = ""
    if agent_available and run_id:
        agent_note = f"\n> Agent dispatched (run: {run_id[:8]}...)"
    else:
        agent_note = "\n> Agent unavailable, using local analysis"

    yield _emit({
        "stage": "orchestrator_planning",
        "title": "Risk Orchestrator",
        "status": "completed",
        "trace": f"> Found {len(minerals)} mineral dependencies{agent_note}\n> Dispatching sub-agents...",
    })

    # Stage 2: trade_intel
    yield _emit({
        "stage": "trade_intel",
        "title": "Trade Intelligence Agent",
        "status": "active",
        "trace": f"> Querying trade flows for {len(minerals)} minerals\n> Computing HHI concentration indices...",
    })

    if agent_available and run_client and run_id:
        # Poll agent — trade_intel phase (first ~24s / 12 polls)
        poll_count = 0
        max_trade_polls = 12
        agent_completed = False
        agent_text = ""
        consecutive_errors = 0

        while poll_count < max_trade_polls:
            time.sleep(2)
            poll_count += 1
            try:
                status = run_client.get_run_status(run_id)
                consecutive_errors = 0
            except Exception as e:
                logger.warning(f"Poll error: {e}")
                consecutive_errors += 1
                if consecutive_errors >= 5:
                    agent_available = False
                    break
                continue

            run_state = status.get("status", "").lower()

            if run_state == "completed":
                result_data = status.get("result", {}).get("data", {})
                message = result_data.get("message", {})
                content_list = message.get("content", [])
                for c in content_list:
                    if isinstance(c, dict) and "text" in c:
                        agent_text = c["text"]
                        break
                    elif isinstance(c, str):
                        agent_text = c
                        break
                agent_completed = True
                break

            if run_state in ("failed", "cancelled"):
                logger.warning(f"Agent run {run_state}")
                agent_available = False
                break

            if poll_count % 3 == 0:
                yield _emit({
                    "stage": "trade_intel",
                    "title": "Trade Intelligence Agent",
                    "status": "active",
                    "trace": f"> Agent processing... ({poll_count * 2}s elapsed)\n> Analyzing trade concentration data...",
                })
    else:
        time.sleep(0.3)

    trade_score = local_result["breakdown"]["trade"]
    flows = local_result.get("trade_flows", [])

    yield _emit({
        "stage": "trade_intel",
        "title": "Trade Intelligence Agent",
        "status": "completed",
        "trace": f"> Analyzed {len(flows)} trade routes\n> Trade risk score: {trade_score}",
    })

    # Stage 3: corporate_exposure
    yield _emit({
        "stage": "corporate_exposure",
        "title": "Corporate Exposure Agent",
        "status": "active",
        "trace": "> Scanning USGS supply risk data\n> Cross-referencing SEC filings...",
    })

    if agent_available and run_client and run_id and not agent_completed:
        # Continue polling during corporate_exposure phase
        max_total_polls = 90
        while poll_count < max_total_polls:
            time.sleep(2)
            poll_count += 1
            try:
                status = run_client.get_run_status(run_id)
                consecutive_errors = 0
            except Exception as e:
                logger.warning(f"Poll error: {e}")
                consecutive_errors += 1
                if consecutive_errors >= 5:
                    agent_available = False
                    break
                continue

            run_state = status.get("status", "").lower()

            if run_state == "completed":
                result_data = status.get("result", {}).get("data", {})
                message = result_data.get("message", {})
                content_list = message.get("content", [])
                for c in content_list:
                    if isinstance(c, dict) and "text" in c:
                        agent_text = c["text"]
                        break
                    elif isinstance(c, str):
                        agent_text = c
                        break
                agent_completed = True
                break

            if run_state in ("failed", "cancelled"):
                logger.warning(f"Agent run {run_state}")
                agent_available = False
                break

            if poll_count % 3 == 0:
                yield _emit({
                    "stage": "corporate_exposure",
                    "title": "Corporate Exposure Agent",
                    "status": "active",
                    "trace": f"> Agent still processing... ({poll_count * 2}s elapsed)\n> Evaluating corporate exposure and substitutability...",
                })
    else:
        time.sleep(0.3)

    corporate_score = local_result["breakdown"]["corporate"]
    subst_score = local_result["breakdown"]["substitutability"]

    corp_trace = f"> Corporate exposure score: {corporate_score}\n> Substitutability risk: {subst_score}"
    if agent_available and agent_completed and agent_text:
        excerpt = agent_text[:300] + ("..." if len(agent_text) > 300 else "")
        corp_trace += f"\n> Agent insight: {excerpt}"

    yield _emit({
        "stage": "corporate_exposure",
        "title": "Corporate Exposure Agent",
        "status": "completed",
        "trace": corp_trace,
    })

    # Stage 4: orchestrator_scoring
    yield _emit({
        "stage": "orchestrator_scoring",
        "title": "Risk Orchestrator — Scoring",
        "status": "active",
        "trace": "> Computing weighted composite score\n> Weights: trade 40%, corporate 35%, substitutability 25%",
    })

    # Build final result — same shape as local analytics
    result = dict(local_result)

    # Enrich summary with agent text if available
    if agent_available and agent_completed and agent_text:
        result["summary"] = agent_text

    composite_score = result["score"]

    yield _emit({
        "stage": "orchestrator_scoring",
        "title": "Risk Orchestrator — Scoring",
        "status": "completed",
        "trace": f"> Composite risk score: {composite_score}\n> Analysis complete for {company}"
              + ("\n> Enriched with agent analysis" if agent_completed and agent_text else ""),
    })

    time.sleep(0.1)
    yield _emit({"stage": "complete", "result": result})


def run_custom_scenario_generator(company: str, scenario_text: str):
    """
    Main entry point: try agent-based analysis, fall back to keyword simulation.
    Yields SSE-formatted events.
    """
    if ORCHESTRATE_URL and IBM_API_KEY:
        try:
            yield from _try_agent_stream(company, scenario_text)
            return
        except ImportError:
            logger.warning("ibm_watsonx_orchestrate not installed, using fallback")
        except Exception as e:
            logger.warning(f"Agent stream failed ({e}), using fallback")

    yield from _fallback_stream(company, scenario_text)
