"""Tool to summarize mineral-related risk sections from SEC filings."""

import json

from ibm_watsonx_orchestrate.agent_builder.tools import tool


@tool()
def summarize_risk_section(mineral_mentions_json: str) -> str:
    """Summarize mineral supply-chain risk from filing excerpts using Granite.

    Takes extracted mineral mentions and their surrounding context from a
    10-K filing, then produces a concise risk summary with an exposure score.

    Args:
        mineral_mentions_json: JSON string from extract_mineral_dependencies output
            containing {minerals_found, dependencies} with context excerpts.

    Returns:
        JSON string with {company, risk_summary, exposure_score, key_risks} where
        exposure_score is 0-100 and key_risks is an array of risk descriptions.
    """
    # TODO: implement once Granite summarization is available.
    # Implementation will:
    # 1. Parse mineral_mentions_json for dependency contexts
    # 2. Construct a summarization prompt for Granite
    # 3. Extract exposure_score (0-100) based on dependency severity and count
    # 4. Return structured risk summary
    data = json.loads(mineral_mentions_json)
    return json.dumps({
        "filing_url": data.get("filing_url", ""),
        "status": "pending",
        "note": "Summarization requires Granite LLM call at agent runtime",
        "risk_summary": "",
        "exposure_score": 0,
        "key_risks": [],
    })
