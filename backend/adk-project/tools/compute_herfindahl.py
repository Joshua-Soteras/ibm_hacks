"""Tool to compute the Herfindahl-Hirschman Index for supply concentration."""

import json

from ibm_watsonx_orchestrate.agent_builder.tools import tool


@tool()
def compute_herfindahl(trade_data_json: str) -> str:
    """Compute the Herfindahl-Hirschman Index (HHI) from trade flow data.

    The HHI measures market concentration: sum of squared market shares.
    Range: 0 (perfectly diversified) to 10000 (single-source monopoly).
    Thresholds: <1500 = low concentration, 1500-2500 = moderate, >2500 = high.

    Args:
        trade_data_json: JSON string containing a "trade_flows" array where each
            element has a "share_pct" field (0-100 percentage).

    Returns:
        JSON string with {hhi, concentration_level, top_supplier, top_share_pct}.
    """
    data = json.loads(trade_data_json)
    flows = data.get("trade_flows", [])

    if not flows:
        return json.dumps({"hhi": 0, "concentration_level": "unknown", "note": "No trade flow data provided"})

    shares = [f.get("share_pct", 0) for f in flows]
    hhi = round(sum(s ** 2 for s in shares), 2)

    if hhi < 1500:
        level = "low"
    elif hhi < 2500:
        level = "moderate"
    else:
        level = "high"

    top = max(flows, key=lambda f: f.get("share_pct", 0))

    return json.dumps({
        "hhi": hhi,
        "concentration_level": level,
        "top_supplier": top.get("Country", top.get("country", "unknown")),
        "top_share_pct": top.get("share_pct", 0),
    })
