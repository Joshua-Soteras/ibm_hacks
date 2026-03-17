"""Tool to compute composite supply-chain risk score."""

import json
from typing import Optional

from ibm_watsonx_orchestrate.agent_builder.tools import tool

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent))
from _db import get_db_conn, USGS_COL, DEFAULT_RISK_SCORE, strip_mineral_qualifier

WEIGHT_TRADE = 0.40
WEIGHT_CORPORATE = 0.35
WEIGHT_SUBSTITUTABILITY = 0.25

RISK_TO_SCORE = {
    "CRITICAL": 90,
    "HIGH": 70,
    "MODERATE": 50,
    "LOW": 20,
}


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


@tool()
def compute_composite_risk(
    trade_data_json: str,
    corporate_data_json: str,
    mineral_name: Optional[str] = None,
) -> str:
    """Compute a weighted composite risk score from trade and corporate exposure data.

    Formula: 0.40 * trade_risk + 0.35 * corporate_risk + 0.25 * substitutability_risk

    Trade risk is derived from HHI (normalized to 0-100).
    Corporate risk uses the exposure_score from filing analysis.
    Substitutability is derived from USGS Supply Risk when mineral_name is provided,
    otherwise defaults to 50.

    Args:
        trade_data_json: JSON string with {hhi, concentration_level} from compute_herfindahl.
        corporate_data_json: JSON string with {exposure_score} from summarize_risk_section.
        mineral_name: Optional mineral name to look up real substitutability risk from USGS data.

    Returns:
        JSON string with {composite_score, risk_level, breakdown} where composite_score
        is 0-100 and risk_level is low/medium/high/critical.
    """
    trade_data = json.loads(trade_data_json)
    corporate_data = json.loads(corporate_data_json)

    hhi = trade_data.get("hhi", 0)
    trade_risk = _normalize_hhi(hhi)

    corporate_risk = corporate_data.get("exposure_score", 0)

    # Derive substitutability from DB if mineral_name is provided
    substitutability_risk = corporate_data.get("substitutability_risk", DEFAULT_RISK_SCORE)

    if mineral_name:
        base_name = strip_mineral_qualifier(mineral_name)
        conn = get_db_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                f'SELECT "Supply Risk" FROM usgs_minerals WHERE "{USGS_COL}" LIKE ?',
                (f"%{base_name}%",),
            )
            row = cursor.fetchone()
            if row and row["Supply Risk"]:
                risk_str = row["Supply Risk"].upper()
                substitutability_risk = RISK_TO_SCORE.get(risk_str, DEFAULT_RISK_SCORE)
        finally:
            conn.close()

    composite = round(
        WEIGHT_TRADE * trade_risk
        + WEIGHT_CORPORATE * corporate_risk
        + WEIGHT_SUBSTITUTABILITY * substitutability_risk,
        2,
    )

    if composite < 25:
        level = "low"
    elif composite < 50:
        level = "medium"
    elif composite < 75:
        level = "high"
    else:
        level = "critical"

    return json.dumps({
        "composite_score": composite,
        "risk_level": level,
        "breakdown": {
            "trade_risk": round(trade_risk, 2),
            "trade_weight": WEIGHT_TRADE,
            "corporate_risk": round(corporate_risk, 2),
            "corporate_weight": WEIGHT_CORPORATE,
            "substitutability_risk": round(substitutability_risk, 2),
            "substitutability_weight": WEIGHT_SUBSTITUTABILITY,
        },
    })
