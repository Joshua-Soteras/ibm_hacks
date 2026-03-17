import math

import pandas as pd
import sqlite3
import os
import numpy as np

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "mineralwatch.db")

def get_db_conn():
    """Get a database connection and ensure it's valid."""
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Database not found at {DB_PATH}")
    return sqlite3.connect(DB_PATH)

def get_company_list():
    """Get list of unique companies from database."""
    try:
        conn = get_db_conn()
        query = "SELECT DISTINCT Company FROM edgar_filing_details"
        companies = pd.read_sql_query(query, conn)['Company'].tolist()
        conn.close()
    except Exception as e:
        print(f"Database error in get_company_list: {e}")
        return []
    
    clean_companies = []
    for c in companies:
        name = c.split('(')[0].strip()
        if name and name not in clean_companies:
            clean_companies.append(name)
            
    return sorted(clean_companies)

RISK_SCORE_MAP = {'LOW': 20, 'MODERATE': 50, 'HIGH': 70, 'CRITICAL': 90}


def _normalize_hhi(hhi: float) -> float:
    """Map HHI (0-10000) to risk score (0-100) using DOJ/FTC antitrust thresholds."""
    if hhi <= 1500:
        return (hhi / 1500) * 30
    elif hhi <= 2500:
        return 30 + ((hhi - 1500) / 1000) * 30
    elif hhi <= 5000:
        return 60 + ((hhi - 2500) / 2500) * 25
    else:
        return 85 + min((hhi - 5000) / 5000, 1.0) * 15


def compute_hhi(trade_data):
    """Compute Herfindahl-Hirschman Index using Customs Value (USD)."""
    val_col = 'Customs Value (USD)'
    if trade_data.empty or trade_data[val_col].sum() == 0:
        return 0
    
    total_val = trade_data[val_col].sum()
    shares = trade_data.groupby('Country')[val_col].sum() / total_val
    hhi = (shares ** 2).sum()
    return hhi

def _get_trade_data_for_company(company_name, conn, minerals):
    """Get trade flows and compute concentration metrics for a company's minerals."""
    trade_flows = []
    mineral_hhis = []
    val_col = 'Customs Value (USD)'

    for mineral in minerals:
        query_trade = "SELECT * FROM trade_data WHERE Mineral LIKE ?"
        mineral_trade = pd.read_sql_query(query_trade, conn, params=(f"%{mineral}%",))

        if not mineral_trade.empty:
            total_val = mineral_trade[val_col].sum()
            shares = (mineral_trade.groupby('Country')[val_col].sum() / total_val * 100).round(1)

            for country, share in shares.items():
                if share > 0.1:
                    trade_flows.append({
                        "mineral": mineral,
                        "country": country,
                        "share": share,
                        "risk": "high" if share > 50 else "elevated" if share > 20 else "low"
                    })

            hhi = compute_hhi(mineral_trade)
            mineral_hhis.append(hhi)

    avg_hhi = np.mean(mineral_hhis) if mineral_hhis else 0
    trade_score = _normalize_hhi(avg_hhi * 10000)

    return {
        "minerals": minerals,
        "flows": trade_flows,
        "hhis": mineral_hhis,
        "trade_score": trade_score
    }


def _get_corporate_data_for_company(conn, minerals):
    """Compute corporate exposure and substitutability scores from USGS data."""
    placeholders = ','.join(['?'] * len(minerals))
    query_usgs = f"SELECT * FROM usgs_minerals WHERE \"USGS Commodity Name\\n(exact CSV name)\" IN ({placeholders})"
    relevant_usgs = pd.read_sql_query(query_usgs, conn, params=minerals)

    if not relevant_usgs.empty and 'Supply Risk' in relevant_usgs.columns:
        mineral_scores = [
            RISK_SCORE_MAP.get(str(r).upper(), 50)
            for r in relevant_usgs['Supply Risk']
            if pd.notna(r)
        ]
        corporate_score = round(sum(mineral_scores) / len(mineral_scores)) if mineral_scores else 50
    else:
        corporate_score = min(round((len(minerals) / 10.0) * 100), 100)

    subst_scores = []
    if not relevant_usgs.empty and 'Supply Risk' in relevant_usgs.columns:
        for r in relevant_usgs['Supply Risk']:
            if pd.notna(r) and isinstance(r, str):
                subst_scores.append(RISK_SCORE_MAP.get(r.upper(), 50))
    subst_score = round(sum(subst_scores) / len(subst_scores)) if subst_scores else 50

    snippet = ""
    if not relevant_usgs.empty:
        snippet = f"Analysis covers {len(minerals)} minerals with USGS supply risk data."

    return {
        "corporate_score": corporate_score,
        "subst_score": subst_score,
        "snippet": snippet
    }


def analyze_company(company_name):
    """Perform full risk analysis for a given company using SQL."""
    try:
        conn = get_db_conn()

        query_filings = "SELECT * FROM edgar_filing_details WHERE Company LIKE ?"
        company_filings = pd.read_sql_query(query_filings, conn, params=(f"%{company_name}%",))

        if company_filings.empty:
            conn.close()
            return None
    except Exception as e:
        print(f"Error analyzing company {company_name}: {e}")
        return None

    minerals = company_filings['Mineral'].unique().tolist()

    trade_data = _get_trade_data_for_company(company_name, conn, minerals)
    corp_data = _get_corporate_data_for_company(conn, minerals)

    trade_score = trade_data["trade_score"]
    corporate_score = corp_data["corporate_score"]
    subst_score = corp_data["subst_score"]
    composite_score = round(trade_score * 0.40 + corporate_score * 0.35 + subst_score * 0.25)

    summary = company_filings['Snippet'].iloc[0] if 'Snippet' in company_filings.columns else "No specific filing snippets found."

    conn.close()

    return {
        "company": company_name,
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


def get_company_scenarios(company_name):
    """Generate disruption scenarios based on trade concentration for a company."""
    result = analyze_company(company_name)
    if not result:
        return []

    # For each mineral, find the top-1 country by share
    mineral_tops = {}
    for flow in result["trade_flows"]:
        mineral = flow["mineral"]
        if mineral not in mineral_tops or flow["share"] > mineral_tops[mineral]["share"]:
            mineral_tops[mineral] = flow

    scenarios = []
    for mineral, flow in mineral_tops.items():
        if flow["share"] > 30:
            country = flow["country"]
            scenario_id = f"{country.lower().replace(' ', '-')}-{mineral.lower().replace(' ', '-')}"
            scenarios.append({
                "id": scenario_id,
                "title": f"{country} {mineral} Export Ban",
                "country": country,
                "mineral": mineral,
                "impact": "high" if flow["share"] > 50 else "mid",
                "top_share_pct": float(flow["share"])
            })

    scenarios.sort(key=lambda s: s["top_share_pct"], reverse=True)
    return scenarios[:5]


def simulate_company_disruption(company_name, country, mineral, disruption_pct=100.0):
    """Simulate a supply disruption and recompute risk scores."""
    baseline = analyze_company(company_name)
    if not baseline:
        return None

    baseline_score = baseline["score"]
    baseline_trade = baseline["breakdown"]["trade"]
    baseline_corporate = baseline["breakdown"]["corporate"]
    baseline_subst = baseline["breakdown"]["substitutability"]

    # Build disrupted trade flows
    disrupted_flows = []
    supply_gap = 0.0

    for flow in baseline["trade_flows"]:
        if flow["mineral"].lower() == mineral.lower() and flow["country"].lower() == country.lower():
            # This is the disrupted flow
            supply_gap = flow["share"] * (disruption_pct / 100.0)
            remaining_share = flow["share"] * (1 - disruption_pct / 100.0)
            if remaining_share > 0.1:
                disrupted_flows.append({**flow, "share": round(remaining_share, 1), "status": "disrupted"})
            else:
                disrupted_flows.append({**flow, "share": 0, "status": "disrupted"})
        elif flow["mineral"].lower() == mineral.lower():
            # Same mineral, different country — stressed (absorbing demand)
            disrupted_flows.append({**flow, "status": "stressed"})
        else:
            disrupted_flows.append({**flow, "status": "active"})

    # Renormalize same-mineral shares (excluding disrupted)
    same_mineral = [f for f in disrupted_flows if f["mineral"].lower() == mineral.lower() and f["status"] != "disrupted"]
    if same_mineral:
        total_remaining = sum(f["share"] for f in same_mineral)
        if total_remaining > 0:
            scale = (100.0 - supply_gap + supply_gap) / total_remaining  # absorb removed share
            for f in same_mineral:
                f["share"] = round(f["share"] * scale, 1)

    # Recompute HHI for the disrupted mineral
    try:
        conn = get_db_conn()
        minerals = baseline["minerals"]
        mineral_hhis = []
        val_col = 'Customs Value (USD)'
        for m in minerals:
            query_trade = "SELECT * FROM trade_data WHERE Mineral LIKE ?"
            mineral_trade = pd.read_sql_query(query_trade, conn, params=(f"%{m}%",))
            if not mineral_trade.empty:
                if m.lower() == mineral.lower():
                    # Zero out disrupted country
                    mineral_trade.loc[
                        mineral_trade['Country'].str.lower() == country.lower(), val_col
                    ] = mineral_trade.loc[
                        mineral_trade['Country'].str.lower() == country.lower(), val_col
                    ] * (1 - disruption_pct / 100.0)
                hhi = compute_hhi(mineral_trade)
                mineral_hhis.append(hhi)
        conn.close()
    except Exception:
        mineral_hhis = []

    avg_hhi = np.mean(mineral_hhis) if mineral_hhis else 0
    new_trade_score = round(_normalize_hhi(avg_hhi * 10000))

    # Uplift corporate score by 15 (capped at 100) per system design
    new_corporate = min(baseline_corporate + 15, 100)
    new_subst = baseline_subst

    disrupted_score = round(new_trade_score * 0.40 + new_corporate * 0.35 + new_subst * 0.25)
    score_delta = disrupted_score - baseline_score

    if score_delta >= 20:
        severity = "critical"
    elif score_delta >= 10:
        severity = "high"
    elif score_delta >= 5:
        severity = "moderate"
    else:
        severity = "low"

    return {
        "company": company_name,
        "baseline_score": baseline_score,
        "disrupted_score": disrupted_score,
        "score_delta": score_delta,
        "severity": severity,
        "supply_gap_pct": round(supply_gap, 1),
        "disrupted_mineral": mineral,
        "disrupted_country": country,
        "disrupted_breakdown": {
            "trade": new_trade_score,
            "corporate": new_corporate,
            "substitutability": new_subst
        },
        "disrupted_trade_flows": disrupted_flows
    }

def get_all_minerals():
    """Get list of all critical minerals tracked."""
    conn = get_db_conn()
    query = "SELECT DISTINCT Mineral FROM edgar_filing_details"
    minerals = pd.read_sql_query(query, conn)['Mineral'].tolist()
    conn.close()
    return sorted(minerals)

def get_company_minerals(company_name):
    """Get minerals for a specific company."""
    conn = get_db_conn()
    query = "SELECT DISTINCT Mineral FROM edgar_filing_details WHERE Company LIKE ?"
    minerals = pd.read_sql_query(query, conn, params=(f"%{company_name}%",))['Mineral'].tolist()
    conn.close()
    return minerals

def get_mineral_risk(mineral_name):
    """Get trade concentration and supply risk for a single mineral."""
    conn = get_db_conn()
    
    # Trade concentration
    query_trade = "SELECT * FROM trade_data WHERE Mineral LIKE ?"
    df_trade = pd.read_sql_query(query_trade, conn, params=(f"%{mineral_name}%",))
    
    hhi = compute_hhi(df_trade)
    
    # Supply risk from USGS
    query_usgs = "SELECT \"Supply Risk\" FROM usgs_minerals WHERE \"USGS Commodity Name\\n(exact CSV name)\" LIKE ?"
    df_usgs = pd.read_sql_query(query_usgs, conn, params=(f"%{mineral_name}%",))
    
    supply_risk = df_usgs['Supply Risk'].iloc[0] if not df_usgs.empty else "UNKNOWN"
    
    conn.close()
    return {
        "mineral": mineral_name,
        "hhi": round(hhi, 3),
        "concentration_score": round(_normalize_hhi(hhi * 10000), 1),
        "supply_risk": supply_risk
    }
