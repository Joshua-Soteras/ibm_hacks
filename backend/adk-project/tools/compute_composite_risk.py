"""Tool to compute composite supply-chain risk score."""

import json

from ibm_watsonx_orchestrate.agent_builder.tools import tool

WEIGHT_TRADE = 0.40
WEIGHT_CORPORATE = 0.35
WEIGHT_SUBSTITUTABILITY = 0.25


@tool()
def compute_composite_risk(trade_data_json: str, corporate_data_json: str) -> str:
    """Compute a weighted composite risk score from trade and corporate exposure data.

    Formula: 0.40 * trade_risk + 0.35 * corporate_risk + 0.25 * substitutability_risk

    Trade risk is derived from HHI (normalized to 0-100).
    Corporate risk uses the exposure_score from filing analysis.
    Substitutability defaults to 50 if not provided (pending KB enrichment).

    Args:
        trade_data_json: JSON string with {hhi, concentration_level} from compute_herfindahl.
        corporate_data_json: JSON string with {exposure_score} from summarize_risk_section.

    Returns:
        JSON string with {composite_score, risk_level, breakdown} where composite_score
        is 0-100 and risk_level is low/medium/high/critical.
    """
    trade_data = json.loads(trade_data_json)
    corporate_data = json.loads(corporate_data_json)

    hhi = trade_data.get("hhi", 0)
    trade_risk = min(hhi / 100, 100)

    corporate_risk = corporate_data.get("exposure_score", 0)

    substitutability_risk = corporate_data.get("substitutability_risk", 50)

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
