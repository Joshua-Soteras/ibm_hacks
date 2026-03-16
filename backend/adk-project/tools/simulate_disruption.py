"""Tool to simulate supply disruption scenarios."""

import json

from ibm_watsonx_orchestrate.agent_builder.tools import tool


@tool()
def simulate_disruption(scenario_json: str, baseline_data_json: str) -> str:
    """Simulate a supply disruption by removing a country-mineral pair and re-scoring.

    Takes a disruption scenario (e.g. "China stops exporting gallium") and
    baseline trade data, removes the affected flows, recalculates concentration
    indices, and estimates the impact.

    Args:
        scenario_json: JSON string with {country, mineral, disruption_pct} where
            disruption_pct is 0-100 representing the percentage of supply cut.
        baseline_data_json: JSON string with {trade_flows} array from query_import_volumes.

    Returns:
        JSON string with {scenario, baseline_hhi, disrupted_hhi, hhi_delta,
        supply_gap_pct, affected_value_usd, severity}.
    """
    scenario = json.loads(scenario_json)
    baseline = json.loads(baseline_data_json)

    target_country = scenario.get("country", "")
    disruption_pct = scenario.get("disruption_pct", 100) / 100
    flows = baseline.get("trade_flows", [])

    if not flows:
        return json.dumps({"error": "No baseline trade flows provided"})

    baseline_shares = [f.get("share_pct", 0) for f in flows]
    baseline_hhi = round(sum(s ** 2 for s in baseline_shares), 2)

    disrupted_flows = []
    removed_value = 0
    for f in flows:
        country = f.get("Country", f.get("country", ""))
        if country.lower() == target_country.lower():
            remaining_share = f.get("share_pct", 0) * (1 - disruption_pct)
            removed_value += f.get("total_value_usd", 0) * disruption_pct
            if remaining_share > 0:
                disrupted_flows.append({**f, "share_pct": remaining_share})
        else:
            disrupted_flows.append(f)

    total_remaining = sum(f.get("share_pct", 0) for f in disrupted_flows)
    if total_remaining > 0:
        for f in disrupted_flows:
            f["share_pct"] = round(f["share_pct"] / total_remaining * 100, 2)

    disrupted_shares = [f.get("share_pct", 0) for f in disrupted_flows]
    disrupted_hhi = round(sum(s ** 2 for s in disrupted_shares), 2) if disrupted_shares else 10000

    hhi_delta = round(disrupted_hhi - baseline_hhi, 2)
    target_share = next(
        (f.get("share_pct", 0) for f in flows
         if f.get("Country", f.get("country", "")).lower() == target_country.lower()),
        0,
    )
    supply_gap_pct = round(target_share * disruption_pct, 2)

    if supply_gap_pct > 50:
        severity = "critical"
    elif supply_gap_pct > 25:
        severity = "high"
    elif supply_gap_pct > 10:
        severity = "moderate"
    else:
        severity = "low"

    return json.dumps({
        "scenario": scenario,
        "baseline_hhi": baseline_hhi,
        "disrupted_hhi": disrupted_hhi,
        "hhi_delta": hhi_delta,
        "supply_gap_pct": supply_gap_pct,
        "affected_value_usd": round(removed_value, 2),
        "severity": severity,
    })
