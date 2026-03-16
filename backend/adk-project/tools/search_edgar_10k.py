"""Tool to search SEC EDGAR for 10-K filings mentioning critical minerals."""

import json
from pathlib import Path
from typing import Optional

import requests
from ibm_watsonx_orchestrate.agent_builder.tools import tool

REFERENCE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "reference"
EDGAR_SEARCH_URL = "https://efts.sec.gov/LATEST/search-index"
EDGAR_FULLTEXT_URL = "https://efts.sec.gov/LATEST/search-index"
USER_AGENT = "MineralWatch/1.0 (supply-chain-research)"


def _load_ciks() -> dict:
    cik_path = REFERENCE_DIR / "company_ciks.json"
    if cik_path.exists():
        with open(cik_path) as f:
            return json.load(f)
    return {}


@tool()
def search_edgar_10k(company_name: str, mineral_keywords: Optional[str] = None) -> str:
    """Search SEC EDGAR full-text search for 10-K filings that mention minerals.

    Args:
        company_name: Company name to search (e.g. "NVIDIA", "Intel").
        mineral_keywords: Optional comma-separated mineral keywords to search for
            within filings (e.g. "gallium,germanium"). Defaults to all tracked minerals.

    Returns:
        JSON string with an array of matching filings: {filing_url, date, excerpt}.
    """
    ciks = _load_ciks()
    cik = ciks.get(company_name)

    if mineral_keywords is None:
        mineral_keywords = "gallium,germanium,tungsten,cobalt,rare earth"

    keywords = [k.strip() for k in mineral_keywords.split(",")]
    query = f'formType:"10-K" AND ({" OR ".join(keywords)})'

    params = {
        "q": query,
        "dateRange": "custom",
        "startdt": "2020-01-01",
        "enddt": "2026-12-31",
        "forms": "10-K",
    }
    if cik is not None:
        params["entityName"] = str(cik)

    try:
        resp = requests.get(
            "https://efts.sec.gov/LATEST/search-index",
            params=params,
            headers={"User-Agent": USER_AGENT},
            timeout=15,
        )
        resp.raise_for_status()
        results = resp.json()
    except requests.RequestException as e:
        return json.dumps({"error": f"EDGAR API request failed: {str(e)}", "company": company_name})

    hits = results.get("hits", {}).get("hits", [])
    filings = []
    for hit in hits[:10]:
        source = hit.get("_source", {})
        filings.append({
            "filing_url": source.get("file_url", ""),
            "date": source.get("file_date", ""),
            "form_type": source.get("form_type", "10-K"),
            "company": source.get("entity_name", company_name),
            "excerpt": source.get("text", "")[:500],
        })

    return json.dumps({
        "company": company_name,
        "keywords": keywords,
        "filings_found": len(filings),
        "filings": filings,
    })
