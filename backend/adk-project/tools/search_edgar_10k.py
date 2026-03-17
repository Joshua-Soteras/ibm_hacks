"""Tool to search SEC EDGAR for 10-K filings mentioning critical minerals."""

import json
from typing import Optional
from urllib.parse import quote

import requests
from ibm_watsonx_orchestrate.agent_builder.tools import tool

try:
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parent))
    from _api import is_api_mode, api_get, BACKEND_CONNECTION
    from _db import get_db_conn
except (ImportError, ModuleNotFoundError):
    import os as _os, requests as _requests
    BACKEND_CONNECTION = {"app_id": "backend_api", "type": "key_value_creds"}
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
    def get_db_conn():
        raise RuntimeError("Local DB unavailable in cloud. Ensure BACKEND_API_URL is set.")

EDGAR_SEARCH_URL = "https://efts.sec.gov/LATEST/search-index"
USER_AGENT = "MineralWatch/1.0 (supply-chain-research)"


def _lookup_cik(company_name: str) -> Optional[int]:
    """Look up a company's CIK from the edgar_company_filings table."""
    if is_api_mode():
        try:
            data = api_get(f"/api/edgar/cik/{quote(company_name, safe='')}")
            return data.get("cik")
        except Exception:
            return None
    conn = get_db_conn()
    try:
        row = conn.execute(
            "SELECT CIK FROM edgar_company_filings WHERE Company LIKE ? LIMIT 1",
            (f"%{company_name}%",),
        ).fetchone()
        return row["CIK"] if row else None
    finally:
        conn.close()


@tool(expected_credentials=[BACKEND_CONNECTION])
def search_edgar_10k(
    company_name: str,
    mineral_keywords: Optional[str] = None,
    since_date: Optional[str] = None,
) -> str:
    """Search SEC EDGAR full-text search for 10-K filings that mention minerals.

    Args:
        company_name: Company name to search (e.g. "NVIDIA", "Intel").
        mineral_keywords: Optional comma-separated mineral keywords to search for
            within filings (e.g. "gallium,germanium"). Defaults to all tracked minerals.
        since_date: Optional start date (YYYY-MM-DD) to limit results to filings
            after this date. Useful for checking filings newer than the DB snapshot.
            Defaults to "2020-01-01".

    Returns:
        JSON string with an array of matching filings: {filing_url, date, excerpt}.
    """
    cik = _lookup_cik(company_name)

    if mineral_keywords is None:
        mineral_keywords = "gallium,germanium,tungsten,cobalt,rare earth"

    keywords = [k.strip() for k in mineral_keywords.split(",")]
    query = " OR ".join(f'"{k}"' for k in keywords)

    start_date = since_date if since_date else "2020-01-01"

    params = {
        "q": query,
        "dateRange": "custom",
        "startdt": start_date,
        "enddt": "2026-12-31",
        "forms": "10-K",
    }
    if cik is not None:
        params["entityName"] = company_name

    try:
        resp = requests.get(
            EDGAR_SEARCH_URL,
            params=params,
            headers={"User-Agent": USER_AGENT},
            timeout=15,
        )
        resp.raise_for_status()
        results = resp.json()
    except requests.RequestException as e:
        return json.dumps({"error": f"EDGAR API request failed: {str(e)}", "company": company_name})

    # SEC EFTS API returns {"hits": {"hits": [{"_id": ..., "_source": {...}}, ...]}}
    hits = results.get("hits", {}).get("hits", [])
    filings = []
    for hit in hits[:10]:
        source = hit.get("_source", {})
        filing_url = source.get("file_url", "")
        if not filing_url and source.get("file_num"):
            filing_url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&filenum={source['file_num']}&type=10-K"
        filings.append({
            "filing_url": filing_url,
            "date": source.get("file_date", ""),
            "form_type": source.get("form_type", "10-K"),
            "company": source.get("entity_name", company_name),
            "cik": source.get("entity_id", cik),
            "excerpt": source.get("text", "")[:500],
        })

    return json.dumps({
        "company": company_name,
        "cik_used": cik,
        "keywords": keywords,
        "since_date": start_date,
        "filings_found": len(filings),
        "filings": filings,
    })
