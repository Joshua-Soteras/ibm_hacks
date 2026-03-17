"""Tool to summarize mineral-related risk from EDGAR data."""

import json

from ibm_watsonx_orchestrate.agent_builder.tools import tool

from ._db import get_db_conn

RISK_SCORE_MAP = {
    "CRITICAL": 90,
    "HIGH": 70,
    "MODERATE": 50,
    "LOW": 20,
}


@tool()
def summarize_risk_section(company_name: str) -> str:
    """Summarize mineral supply-chain risk for a company using EDGAR data.

    Queries blind-spot analysis, EDGAR summary, and filing details to produce
    a risk summary with an exposure score.

    Args:
        company_name: Name of the company to summarize risk for.

    Returns:
        JSON string with {company, risk_summary, exposure_score, key_risks} where
        exposure_score is 0-100 and key_risks is an array of risk descriptions.
    """
    conn = get_db_conn()
    cursor = conn.cursor()

    # Get minerals this company is exposed to
    cursor.execute(
        'SELECT DISTINCT Mineral FROM edgar_filing_details WHERE Company LIKE ?',
        (f"%{company_name}%",),
    )
    minerals = [r["Mineral"] for r in cursor.fetchall()]

    if not minerals:
        conn.close()
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
        # Get blind-spot analysis
        cursor.execute(
            'SELECT * FROM edgar_blind_spot_analysis WHERE Mineral LIKE ?',
            (f"%{mineral}%",),
        )
        blind_row = cursor.fetchone()

        # Get EDGAR summary
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

        score = RISK_SCORE_MAP.get(risk_level.upper() if isinstance(risk_level, str) else "", 30)
        total_risk_score += score
        risk_count += 1

        # Build risk description
        risk_desc = f"{mineral}: {risk_level} supply risk"
        if assessment:
            risk_desc += f" — {assessment}"
        key_risks.append(risk_desc)

    exposure_score = round(total_risk_score / risk_count) if risk_count > 0 else 0

    # Build summary text
    critical_minerals = [m for m, kr in zip(minerals, key_risks) if "CRITICAL" in kr.upper()]
    high_minerals = [m for m, kr in zip(minerals, key_risks) if "HIGH" in kr.upper()]

    summary_parts = [f"{company_name} has exposure to {len(minerals)} critical mineral(s)."]
    if critical_minerals:
        summary_parts.append(f"Critical risk: {', '.join(critical_minerals)}.")
    if high_minerals:
        summary_parts.append(f"High risk: {', '.join(high_minerals)}.")

    conn.close()

    return json.dumps({
        "company": company_name,
        "risk_summary": " ".join(summary_parts),
        "exposure_score": exposure_score,
        "key_risks": key_risks,
    })
