"""Tool to query import volume data for critical minerals from the database."""

import json
from typing import Optional
from urllib.parse import quote

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


def _via_api(mineral_name: str, year: Optional[int]) -> str:
    try:
        params = {}
        if year is not None:
            params["year"] = year
        data = api_get(f"/api/mineral/trade/{quote(mineral_name, safe='')}", params=params)
        return json.dumps(data)
    except Exception as e:
        return json.dumps({"error": f"Backend API unavailable: {e}"})


def _via_db(mineral_name: str, year: Optional[int]) -> str:
    conn = get_db_conn()
    try:
        cursor = conn.cursor()

        if year is not None:
            cursor.execute(
                'SELECT Country, SUM("Customs Value (USD)") as total_value '
                'FROM trade_data WHERE Mineral LIKE ? AND Year = ? '
                'GROUP BY Country ORDER BY total_value DESC',
                (f"%{mineral_name}%", year),
            )
        else:
            cursor.execute(
                'SELECT Country, SUM("Customs Value (USD)") as total_value '
                'FROM trade_data WHERE Mineral LIKE ? '
                'GROUP BY Country ORDER BY total_value DESC',
                (f"%{mineral_name}%",),
            )

        rows = cursor.fetchall()

        if not rows:
            return json.dumps({
                "mineral": mineral_name.lower(),
                "year": year,
                "trade_flows": [],
                "note": "No trade data found for this mineral.",
            })

        total = sum(r["total_value"] for r in rows)
        trade_flows = []
        for r in rows:
            val = r["total_value"]
            trade_flows.append({
                "country": r["Country"],
                "total_value_usd": val,
                "share_pct": round(val / total * 100, 2) if total > 0 else 0.0,
            })

        return json.dumps({
            "mineral": mineral_name.lower(),
            "year": year,
            "trade_flows": trade_flows,
        })
    finally:
        conn.close()


@tool(expected_credentials=[BACKEND_CONNECTION])
def query_import_volumes(mineral_name: str, year: Optional[int] = None) -> str:
    """Query import volumes for a critical mineral, grouped by source country.

    Args:
        mineral_name: Name of the mineral (e.g. gallium, germanium, tungsten, cobalt, rare earths).
        year: Optional year to filter data. If omitted, returns all available years.

    Returns:
        JSON string with {mineral, year, trade_flows} where trade_flows is an
        array of {country, total_value_usd, share_pct} sorted by value descending.
    """
    if is_api_mode():
        return _via_api(mineral_name, year)
    return _via_db(mineral_name, year)
