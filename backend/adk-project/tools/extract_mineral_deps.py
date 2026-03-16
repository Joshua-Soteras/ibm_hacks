"""Tool to extract mineral dependencies from SEC filing text via NER."""

import json

from ibm_watsonx_orchestrate.agent_builder.tools import tool


@tool()
def extract_mineral_dependencies(filing_url: str) -> str:
    """Extract mineral dependency mentions from a SEC 10-K filing using NER.

    Fetches the filing HTML, identifies mineral names, supply-chain terms,
    and geographic references, then returns structured dependency data.

    Args:
        filing_url: URL of the SEC EDGAR filing to analyze.

    Returns:
        JSON string with {filing_url, minerals_found, dependencies} where
        dependencies is an array of {mineral, context, severity}.
    """
    # TODO: implement once Granite LLM NER extraction is available.
    # Implementation will:
    # 1. Fetch filing HTML from filing_url
    # 2. Extract text from relevant sections (Item 1, Item 1A Risk Factors)
    # 3. Run Granite NER to identify mineral mentions and supply chain context
    # 4. Classify severity based on dependency language
    return json.dumps({
        "filing_url": filing_url,
        "status": "pending",
        "note": "NER extraction requires Granite LLM call at agent runtime",
        "minerals_found": [],
        "dependencies": [],
    })
