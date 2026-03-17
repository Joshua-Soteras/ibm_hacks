"""Tool to extract mineral dependencies for a company from the database."""

import json
from urllib.parse import quote

from ibm_watsonx_orchestrate.agent_builder.tools import tool

try:
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parent))
    from _api import is_api_mode, api_get, BACKEND_CONNECTION
    from _db import get_db_conn, USGS_COL, strip_mineral_qualifier
except (ImportError, ModuleNotFoundError):
    import os as _os, re as _re, requests as _requests
    BACKEND_CONNECTION = {"app_id": "backend_api", "type": "key_value_creds"}
    USGS_COL = 'USGS Commodity Name\n(exact CSV name)'
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
    def strip_mineral_qualifier(name):
        name = _re.sub(r"\s*\(.*?\)", "", name); return name.strip("* ").strip()
    def get_db_conn():
        raise RuntimeError("Local DB unavailable in cloud. Ensure BACKEND_API_URL is set.")

SUPPLY_RISK_SEVERITY = {
    "CRITICAL": "critical",
    "HIGH": "high",
    "MODERATE": "moderate",
    "LOW": "low",
}


def _via_api(company_name: str) -> str:
    try:
        data = api_get(f"/api/company/dependencies/{quote(company_name, safe='')}")
        return json.dumps(data)
    except Exception as e:
        return json.dumps({"error": f"Backend API unavailable: {e}"})


def _via_db(company_name: str) -> str:
    conn = get_db_conn()
    try:
        cursor = conn.cursor()

        cursor.execute(
            'SELECT * FROM edgar_mineral_company_matrix WHERE "Company / Mineral" LIKE ?',
            (f"%{company_name}%",),
        )
        matrix_row = cursor.fetchone()

        if not matrix_row:
            cursor.execute(
                'SELECT Mineral, COUNT(*) as mentions '
                'FROM edgar_filing_details WHERE Company LIKE ? GROUP BY Mineral',
                (f"%{company_name}%",),
            )
            filing_minerals = cursor.fetchall()
            if not filing_minerals:
                return json.dumps({
                    "company": company_name,
                    "minerals_found": [],
                    "dependencies": [],
                    "note": "Company not found in EDGAR data.",
                })

            minerals_found = [r["Mineral"] for r in filing_minerals]
            dependencies = []

            for row in filing_minerals:
                mineral = row["Mineral"]

                cursor.execute(
                    'SELECT Snippet FROM edgar_filing_details '
                    'WHERE Company LIKE ? AND Mineral LIKE ? LIMIT 3',
                    (f"%{company_name}%", f"%{mineral}%"),
                )
                snippets = [r["Snippet"] for r in cursor.fetchall() if r["Snippet"]]
                context = "; ".join(snippets) if snippets else "Mentioned in EDGAR filings."

                base_name = strip_mineral_qualifier(mineral)
                cursor.execute(
                    f'SELECT "Supply Risk" FROM usgs_minerals WHERE "{USGS_COL}" LIKE ?',
                    (f"%{base_name}%",),
                )
                risk_row = cursor.fetchone()
                risk_level = risk_row["Supply Risk"] if risk_row else "UNKNOWN"
                severity = SUPPLY_RISK_SEVERITY.get(
                    risk_level.upper() if isinstance(risk_level, str) else "", "unknown"
                )

                dependencies.append({
                    "mineral": mineral,
                    "context": context[:500],
                    "severity": severity,
                })

            severity_order = {"critical": 0, "high": 1, "moderate": 2, "low": 3, "unknown": 4}
            dependencies.sort(key=lambda d: severity_order.get(d["severity"], 4))

            return json.dumps({
                "company": company_name,
                "minerals_found": minerals_found,
                "dependencies": dependencies,
                "source": "edgar_filing_details",
            })

        matrix_cols = [desc[0] for desc in cursor.description]
        matrix_data = dict(zip(matrix_cols, matrix_row))

        minerals_found = []
        for col, val in matrix_data.items():
            if col == "Company / Mineral":
                continue
            if val and val != 0 and val != "0":
                minerals_found.append(col)

        dependencies = []

        for mineral in minerals_found:
            cursor.execute(
                'SELECT Snippet FROM edgar_filing_details '
                'WHERE Company LIKE ? AND Mineral LIKE ? LIMIT 3',
                (f"%{company_name}%", f"%{mineral}%"),
            )
            snippets = [r["Snippet"] for r in cursor.fetchall() if r["Snippet"]]
            context = "; ".join(snippets) if snippets else "Mentioned in EDGAR filings."

            base_name = strip_mineral_qualifier(mineral)
            cursor.execute(
                f'SELECT "Supply Risk" FROM usgs_minerals WHERE "{USGS_COL}" LIKE ?',
                (f"%{base_name}%",),
            )
            risk_row = cursor.fetchone()
            risk_level = risk_row["Supply Risk"] if risk_row else "UNKNOWN"
            severity = SUPPLY_RISK_SEVERITY.get(
                risk_level.upper() if isinstance(risk_level, str) else "", "unknown"
            )

            dependencies.append({
                "mineral": mineral,
                "context": context[:500],
                "severity": severity,
            })

        severity_order = {"critical": 0, "high": 1, "moderate": 2, "low": 3, "unknown": 4}
        dependencies.sort(key=lambda d: severity_order.get(d["severity"], 4))

        return json.dumps({
            "company": company_name,
            "minerals_found": minerals_found,
            "dependencies": dependencies,
        })
    finally:
        conn.close()


@tool(expected_credentials=[BACKEND_CONNECTION])
def extract_mineral_dependencies(company_name: str) -> str:
    """Extract mineral dependencies for a company from EDGAR filing data.

    Queries the mineral-company matrix and filing details to identify which
    critical minerals a company is exposed to, with severity derived from
    USGS supply risk ratings.

    Args:
        company_name: Name of the company to analyze (e.g. "Intel", "TSMC").

    Returns:
        JSON string with {company, minerals_found, dependencies} where
        dependencies is an array of {mineral, context, severity}.
    """
    if is_api_mode():
        return _via_api(company_name)
    return _via_db(company_name)
