import math
import re

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

USGS_COL = 'USGS Commodity Name\n(exact CSV name)'


def strip_mineral_qualifier(name: str) -> str:
    """Strip parenthetical qualifiers and trailing asterisks from mineral names."""
    name = re.sub(r"\s*\(.*?\)", "", name)
    name = name.strip("* ").strip()
    return name


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


# --- ADK TOOL CALLBACK FUNCTIONS ---

def get_mineral_trade_flows(mineral_name, year=None):
    """Get import volumes for a mineral grouped by source country."""
    conn = get_db_conn()
    try:
        cursor = conn.cursor()
        if year is not None:
            cursor.execute(
                'SELECT Country, SUM("Customs Value (USD)") as total_value '
                'FROM trade_data WHERE Mineral LIKE ? AND Year = ? '
                'GROUP BY Country ORDER BY total_value DESC',
                (f"%{mineral_name}%", year),
            )
        else:
            cursor.execute(
                'SELECT Country, SUM("Customs Value (USD)") as total_value '
                'FROM trade_data WHERE Mineral LIKE ? '
                'GROUP BY Country ORDER BY total_value DESC',
                (f"%{mineral_name}%",),
            )
        rows = cursor.fetchall()
        if not rows:
            return {
                "mineral": mineral_name.lower(),
                "year": year,
                "trade_flows": [],
                "note": "No trade data found for this mineral.",
            }
        total = sum(r[1] for r in rows)
        trade_flows = []
        for r in rows:
            val = r[1]
            trade_flows.append({
                "country": r[0],
                "total_value_usd": val,
                "share_pct": round(val / total * 100, 2) if total > 0 else 0.0,
            })
        return {
            "mineral": mineral_name.lower(),
            "year": year,
            "trade_flows": trade_flows,
        }
    finally:
        conn.close()


def get_mineral_profile_data(mineral_name):
    """Get a structured mineral profile from USGS, EDGAR summary, and blind-spot data."""
    conn = get_db_conn()
    try:
        cursor = conn.cursor()

        COL_MATERIAL = "Material / Compound\nUsed in Fab"
        COL_FUNCTION = "What It Does in the Chip"
        COL_CRITICAL = "Critical Mineral?\n(2025 List)"
        COL_PRODUCER = "Top Producer\n(Country)"
        COL_HTS = "HTS Code\n(USITC DataWeb)"

        cursor.execute(
            f'SELECT * FROM usgs_minerals WHERE "{USGS_COL}" LIKE ?',
            (f"%{mineral_name}%",),
        )
        rows = cursor.fetchall()
        if not rows:
            return {"error": f"Mineral '{mineral_name}' not found in USGS data."}

        cols = [desc[0] for desc in cursor.description]
        usgs_data = dict(zip(cols, rows[0]))

        profile = {
            "mineral": mineral_name.lower(),
            "fab_stage": usgs_data.get("Fab Stage", ""),
            "material_compound": usgs_data.get(COL_MATERIAL, ""),
            "chip_function": usgs_data.get(COL_FUNCTION, ""),
            "critical_mineral": usgs_data.get(COL_CRITICAL, ""),
            "top_producer": usgs_data.get(COL_PRODUCER, ""),
            "supply_risk": usgs_data.get("Supply Risk", ""),
            "hts_code": usgs_data.get(COL_HTS, ""),
        }

        if len(rows) > 1:
            profile["additional_uses"] = []
            for r in rows[1:]:
                d = dict(zip(cols, r))
                profile["additional_uses"].append({
                    "fab_stage": d.get("Fab Stage", ""),
                    "material_compound": d.get(COL_MATERIAL, ""),
                    "chip_function": d.get(COL_FUNCTION, ""),
                })

        cursor.execute(
            'SELECT * FROM edgar_summary WHERE Mineral LIKE ?',
            (f"%{mineral_name}%",),
        )
        edgar_row = cursor.fetchone()
        if edgar_row:
            edgar_cols = [desc[0] for desc in cursor.description]
            edgar_data = dict(zip(edgar_cols, edgar_row))
            profile["edgar_hits"] = edgar_data.get("EDGAR Hits", 0)
            profile["unique_companies"] = edgar_data.get("Unique\nCompanies", 0)
            profile["edgar_risk_alignment"] = edgar_data.get("EDGAR vs Risk\nAlignment", "")

        cursor.execute(
            'SELECT * FROM edgar_blind_spot_analysis WHERE Mineral LIKE ?',
            (f"%{mineral_name}%",),
        )
        blind_row = cursor.fetchone()
        if blind_row:
            blind_cols = [desc[0] for desc in cursor.description]
            blind_data = dict(zip(blind_cols, blind_row))
            profile["blind_spot_assessment"] = blind_data.get("Assessment", "")
            profile["recommended_action"] = blind_data.get("Action", "")

        return profile
    finally:
        conn.close()


SUPPLY_RISK_SEVERITY = {
    "CRITICAL": "critical",
    "HIGH": "high",
    "MODERATE": "moderate",
    "LOW": "low",
}


def get_company_dependencies(company_name):
    """Extract mineral dependencies for a company from EDGAR data."""
    conn = get_db_conn()
    try:
        cursor = conn.cursor()

        cursor.execute(
            'SELECT * FROM edgar_mineral_company_matrix WHERE "Company / Mineral" LIKE ?',
            (f"%{company_name}%",),
        )
        matrix_row = cursor.fetchone()

        if not matrix_row:
            # Fallback: build from edgar_filing_details
            cursor.execute(
                'SELECT Mineral, COUNT(*) as mentions '
                'FROM edgar_filing_details WHERE Company LIKE ? GROUP BY Mineral',
                (f"%{company_name}%",),
            )
            filing_minerals = cursor.fetchall()
            if not filing_minerals:
                return {
                    "company": company_name,
                    "minerals_found": [],
                    "dependencies": [],
                    "note": "Company not found in EDGAR data.",
                }

            minerals_found = [r[0] for r in filing_minerals]
            dependencies = []
            for row in filing_minerals:
                mineral = row[0]
                cursor.execute(
                    'SELECT Snippet FROM edgar_filing_details '
                    'WHERE Company LIKE ? AND Mineral LIKE ? LIMIT 3',
                    (f"%{company_name}%", f"%{mineral}%"),
                )
                snippets = [r[0] for r in cursor.fetchall() if r[0]]
                context = "; ".join(snippets) if snippets else "Mentioned in EDGAR filings."

                base_name = strip_mineral_qualifier(mineral)
                cursor.execute(
                    f'SELECT "Supply Risk" FROM usgs_minerals WHERE "{USGS_COL}" LIKE ?',
                    (f"%{base_name}%",),
                )
                risk_row = cursor.fetchone()
                risk_level = risk_row[0] if risk_row else "UNKNOWN"
                severity = SUPPLY_RISK_SEVERITY.get(
                    risk_level.upper() if isinstance(risk_level, str) else "", "unknown"
                )
                dependencies.append({
                    "mineral": mineral,
                    "context": context[:500],
                    "severity": severity,
                })

            severity_order = {"critical": 0, "high": 1, "moderate": 2, "low": 3, "unknown": 4}
            dependencies.sort(key=lambda d: severity_order.get(d["severity"], 4))
            return {
                "company": company_name,
                "minerals_found": minerals_found,
                "dependencies": dependencies,
                "source": "edgar_filing_details",
            }

        cols = [desc[0] for desc in cursor.description]
        matrix_data = dict(zip(cols, matrix_row))

        minerals_found = []
        for col, val in matrix_data.items():
            if col == "Company / Mineral":
                continue
            if val and val != 0 and val != "0":
                minerals_found.append(col)

        dependencies = []
        for mineral in minerals_found:
            cursor.execute(
                'SELECT Snippet FROM edgar_filing_details '
                'WHERE Company LIKE ? AND Mineral LIKE ? LIMIT 3',
                (f"%{company_name}%", f"%{mineral}%"),
            )
            snippets = [r[0] for r in cursor.fetchall() if r[0]]
            context = "; ".join(snippets) if snippets else "Mentioned in EDGAR filings."

            base_name = strip_mineral_qualifier(mineral)
            cursor.execute(
                f'SELECT "Supply Risk" FROM usgs_minerals WHERE "{USGS_COL}" LIKE ?',
                (f"%{base_name}%",),
            )
            risk_row = cursor.fetchone()
            risk_level = risk_row[0] if risk_row else "UNKNOWN"
            severity = SUPPLY_RISK_SEVERITY.get(
                risk_level.upper() if isinstance(risk_level, str) else "", "unknown"
            )
            dependencies.append({
                "mineral": mineral,
                "context": context[:500],
                "severity": severity,
            })

        severity_order = {"critical": 0, "high": 1, "moderate": 2, "low": 3, "unknown": 4}
        dependencies.sort(key=lambda d: severity_order.get(d["severity"], 4))
        return {
            "company": company_name,
            "minerals_found": minerals_found,
            "dependencies": dependencies,
        }
    finally:
        conn.close()


def get_risk_summary(company_name, mineral_name=None):
    """Summarize mineral supply-chain risk using EDGAR data."""
    conn = get_db_conn()
    try:
        cursor = conn.cursor()

        # Mineral-centric mode
        if mineral_name:
            base_name = strip_mineral_qualifier(mineral_name)
            cursor.execute(
                'SELECT COUNT(DISTINCT Company) as company_count, COUNT(*) as total_hits '
                'FROM edgar_filing_details WHERE Mineral LIKE ?',
                (f"%{base_name}%",),
            )
            row = cursor.fetchone()
            company_count = row[0] if row else 0
            total_hits = row[1] if row else 0

            if company_count == 0:
                return {
                    "mineral": mineral_name,
                    "risk_summary": f"No EDGAR filing data found for mineral {mineral_name}.",
                    "exposure_score": 0,
                    "key_risks": [],
                    "mode": "mineral_centric",
                }

            cursor.execute(
                f'SELECT "Supply Risk" FROM usgs_minerals WHERE "{USGS_COL}" LIKE ?',
                (f"%{base_name}%",),
            )
            usgs_row = cursor.fetchone()
            supply_risk = usgs_row[0].upper() if usgs_row and usgs_row[0] else "UNKNOWN"
            supply_risk_score = RISK_SCORE_MAP.get(supply_risk, 50)

            log_breadth = math.log(company_count + 1) / math.log(1020 + 1)
            mention_intensity = min((total_hits / company_count) / 5.0, 1.0) if company_count > 0 else 0

            mineral_corporate_score = round(
                supply_risk_score * 0.50
                + log_breadth * 100 * 0.30
                + mention_intensity * 100 * 0.20
            )
            mineral_corporate_score = min(mineral_corporate_score, 100)

            cursor.execute(
                'SELECT Company, COUNT(*) as hits FROM edgar_filing_details '
                'WHERE Mineral LIKE ? GROUP BY Company ORDER BY hits DESC LIMIT 5',
                (f"%{base_name}%",),
            )
            top_companies = cursor.fetchall()
            key_risks = [
                f"{r[0]}: {r[1]} mention(s) of {mineral_name}" for r in top_companies
            ]

            summary = (
                f"{mineral_name} ({supply_risk} supply risk) is mentioned by "
                f"{company_count} companies across {total_hits} filings. "
                f"Mineral-centric corporate exposure score: {mineral_corporate_score}/100."
            )

            return {
                "mineral": mineral_name,
                "risk_summary": summary,
                "exposure_score": mineral_corporate_score,
                "key_risks": key_risks,
                "company_count": company_count,
                "total_hits": total_hits,
                "supply_risk": supply_risk,
                "mode": "mineral_centric",
            }

        # Company-centric mode
        cursor.execute(
            'SELECT DISTINCT Mineral FROM edgar_filing_details WHERE Company LIKE ?',
            (f"%{company_name}%",),
        )
        minerals = [r[0] for r in cursor.fetchall()]

        if not minerals:
            return {
                "company": company_name,
                "risk_summary": "No EDGAR filing data found for this company.",
                "exposure_score": 0,
                "key_risks": [],
            }

        key_risks = []
        total_risk_score = 0
        risk_count = 0

        for mineral in minerals:
            cursor.execute(
                'SELECT * FROM edgar_blind_spot_analysis WHERE Mineral LIKE ?',
                (f"%{mineral}%",),
            )
            blind_row = cursor.fetchone()

            cursor.execute(
                'SELECT * FROM edgar_summary WHERE Mineral LIKE ?',
                (f"%{mineral}%",),
            )
            summary_row = cursor.fetchone()

            risk_level = "UNKNOWN"
            assessment = ""

            if blind_row:
                blind_cols = [desc[0] for desc in cursor.description]
                # re-query for blind_spot columns
                cursor.execute(
                    'SELECT * FROM edgar_blind_spot_analysis WHERE Mineral LIKE ?',
                    (f"%{mineral}%",),
                )
                blind_row = cursor.fetchone()
                blind_cols = [desc[0] for desc in cursor.description]
                blind_data = dict(zip(blind_cols, blind_row))
                risk_level = blind_data.get("Supply Risk", "UNKNOWN") or "UNKNOWN"
                assessment = blind_data.get("Assessment", "") or ""

            score = RISK_SCORE_MAP.get(
                risk_level.upper() if isinstance(risk_level, str) else "",
                50,
            )
            total_risk_score += score
            risk_count += 1

            risk_desc = f"{mineral}: {risk_level} supply risk"
            if summary_row:
                # Re-query to get summary columns properly
                cursor.execute(
                    'SELECT * FROM edgar_summary WHERE Mineral LIKE ?',
                    (f"%{mineral}%",),
                )
                summary_row = cursor.fetchone()
                summary_cols = [desc[0] for desc in cursor.description]
                summary_data = dict(zip(summary_cols, summary_row))
                hits = summary_data.get("EDGAR Hits")
                if hits:
                    risk_desc += f" ({hits} EDGAR hits)"
            if assessment:
                risk_desc += f" — {assessment}"
            key_risks.append(risk_desc)

        exposure_score = round(total_risk_score / risk_count) if risk_count > 0 else 0

        critical_minerals = [m for m, kr in zip(minerals, key_risks) if "CRITICAL" in kr.upper()]
        high_minerals = [m for m, kr in zip(minerals, key_risks) if "HIGH" in kr.upper()]

        summary_parts = [f"{company_name} has exposure to {len(minerals)} critical mineral(s)."]
        if critical_minerals:
            summary_parts.append(f"Critical risk: {', '.join(critical_minerals)}.")
        if high_minerals:
            summary_parts.append(f"High risk: {', '.join(high_minerals)}.")

        return {
            "company": company_name,
            "risk_summary": " ".join(summary_parts),
            "exposure_score": exposure_score,
            "key_risks": key_risks,
        }
    finally:
        conn.close()


def lookup_edgar_cik(company_name):
    """Look up a company's CIK from EDGAR data."""
    conn = get_db_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT CIK FROM edgar_company_filings WHERE Company LIKE ? LIMIT 1",
            (f"%{company_name}%",),
        )
        row = cursor.fetchone()
        return {"company": company_name, "cik": row[0] if row else None}
    finally:
        conn.close()
