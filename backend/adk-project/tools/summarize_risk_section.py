"""Tool to summarize mineral-related risk from EDGAR data."""

import json
import math
from typing import Optional

from ibm_watsonx_orchestrate.agent_builder.tools import tool

try:
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parent))
    from _api import is_api_mode, api_get, BACKEND_CONNECTION
    from _db import get_db_conn, USGS_COL, DEFAULT_RISK_SCORE, strip_mineral_qualifier
except (ImportError, ModuleNotFoundError):
    import os as _os, re as _re, requests as _requests
    BACKEND_CONNECTION = {"app_id": "backend_api", "type": "key_value_creds"}
    USGS_COL = 'USGS Commodity Name\n(exact CSV name)'
    DEFAULT_RISK_SCORE = 50
    _cached_url = None
    def _resolve_backend_url():
        try:
            from ibm_watsonx_orchestrate.run import connections
            c = connections.key_value("backend_api")
            url = c.get("BACKEND_API_URL", "")
            if url: return url.rstrip("/")
        except Exception: pass
        return _os.environ.get("BACKEND_API_URL", "").rstrip("/")
    def _get_url():
        global _cached_url
        if _cached_url is None: _cached_url = _resolve_backend_url()
        return _cached_url
    def is_api_mode(): return bool(_get_url())
    def api_get(path, params=None, timeout=30):
        url = _get_url()
        resp = _requests.get(f"{url}{path}", params=params,
                             headers={"ngrok-skip-browser-warning": "true"}, timeout=timeout)
        resp.raise_for_status(); return resp.json()
    def strip_mineral_qualifier(name):
        name = _re.sub(r"\s*\(.*?\)", "", name); return name.strip("* ").strip()
    def get_db_conn():
        raise RuntimeError("Local DB unavailable in cloud. Ensure BACKEND_API_URL is set.")

RISK_SCORE_MAP = {
    "CRITICAL": 90,
    "HIGH": 70,
    "MODERATE": 50,
    "LOW": 20,
}


def _via_api(company_name: str, mineral_name: Optional[str]) -> str:
    try:
        params = {"company": company_name}
        if mineral_name:
            params["mineral"] = mineral_name
        data = api_get("/api/risk-summary", params=params)
        return json.dumps(data)
    except Exception as e:
        return json.dumps({"error": f"Backend API unavailable: {e}"})


def _mineral_centric_risk(cursor, mineral_name: str) -> dict:
    """Compute mineral-centric corporate risk across all companies."""
    base_name = strip_mineral_qualifier(mineral_name)

    cursor.execute(
        'SELECT COUNT(DISTINCT Company) as company_count, COUNT(*) as total_hits '
        'FROM edgar_filing_details WHERE Mineral LIKE ?',
        (f"%{base_name}%",),
    )
    row = cursor.fetchone()
    company_count = row["company_count"] if row else 0
    total_hits = row["total_hits"] if row else 0

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
    supply_risk = usgs_row["Supply Risk"].upper() if usgs_row and usgs_row["Supply Risk"] else "UNKNOWN"
    supply_risk_score = RISK_SCORE_MAP.get(supply_risk, DEFAULT_RISK_SCORE)

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
        f"{r['Company']}: {r['hits']} mention(s) of {mineral_name}" for r in top_companies
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


def _via_db(company_name: str, mineral_name: Optional[str]) -> str:
    conn = get_db_conn()
    try:
        cursor = conn.cursor()

        if mineral_name:
            return json.dumps(_mineral_centric_risk(cursor, mineral_name))

        cursor.execute(
            'SELECT DISTINCT Mineral FROM edgar_filing_details WHERE Company LIKE ?',
            (f"%{company_name}%",),
        )
        minerals = [r["Mineral"] for r in cursor.fetchall()]

        if not minerals:
            return json.dumps({
                "company": company_name,
                "risk_summary": "No EDGAR filing data found for this company.",
                "exposure_score": 0,
                "key_risks": [],
            })

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
                risk_level = blind_row["Supply Risk"] or "UNKNOWN"
                assessment = blind_row["Assessment"] or ""

            score = RISK_SCORE_MAP.get(
                risk_level.upper() if isinstance(risk_level, str) else "",
                DEFAULT_RISK_SCORE,
            )
            total_risk_score += score
            risk_count += 1

            risk_desc = f"{mineral}: {risk_level} supply risk"
            if summary_row:
                hits = summary_row["EDGAR Hits"]
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

        return json.dumps({
            "company": company_name,
            "risk_summary": " ".join(summary_parts),
            "exposure_score": exposure_score,
            "key_risks": key_risks,
        })
    finally:
        conn.close()


@tool(expected_credentials=[BACKEND_CONNECTION])
def summarize_risk_section(company_name: str, mineral_name: Optional[str] = None) -> str:
    """Summarize mineral supply-chain risk using EDGAR data.

    Two modes:
    - Company-centric (default): risk for a company across all its minerals.
    - Mineral-centric (when mineral_name is provided): corporate exposure for a
      specific mineral across all companies mentioning it.

    Args:
        company_name: Name of the company to summarize risk for.
        mineral_name: Optional mineral name for mineral-centric scoring.
            When provided, computes how broadly this mineral is exposed across
            all companies in the EDGAR database.

    Returns:
        JSON string with {company|mineral, risk_summary, exposure_score, key_risks}
        where exposure_score is 0-100.
    """
    if is_api_mode():
        return _via_api(company_name, mineral_name)
    return _via_db(company_name, mineral_name)
