"""Tool to extract mineral dependencies for a company from the database."""

import json

from ibm_watsonx_orchestrate.agent_builder.tools import tool

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent))
from _db import get_db_conn, USGS_COL, strip_mineral_qualifier

SUPPLY_RISK_SEVERITY = {
    "CRITICAL": "critical",
    "HIGH": "high",
    "MODERATE": "moderate",
    "LOW": "low",
}


@tool()
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
    conn = get_db_conn()
    try:
        cursor = conn.cursor()

        # Get the company's mineral exposures from the matrix
        cursor.execute(
            'SELECT * FROM edgar_mineral_company_matrix WHERE "Company / Mineral" LIKE ?',
            (f"%{company_name}%",),
        )
        matrix_row = cursor.fetchone()

        if not matrix_row:
            return json.dumps({
                "company": company_name,
                "minerals_found": [],
                "dependencies": [],
                "note": "Company not found in EDGAR mineral matrix.",
            })

        matrix_cols = [desc[0] for desc in cursor.description]
        matrix_data = dict(zip(matrix_cols, matrix_row))

        # Find minerals where the company has non-null, non-zero values
        minerals_found = []
        for col, val in matrix_data.items():
            if col == "Company / Mineral":
                continue
            if val and val != 0 and val != "0":
                minerals_found.append(col)

        # Get filing snippets for each mineral
        dependencies = []

        for mineral in minerals_found:
            # Get filing context
            cursor.execute(
                'SELECT Snippet FROM edgar_filing_details '
                'WHERE Company LIKE ? AND Mineral LIKE ? LIMIT 3',
                (f"%{company_name}%", f"%{mineral}%"),
            )
            snippets = [r["Snippet"] for r in cursor.fetchall() if r["Snippet"]]
            context = "; ".join(snippets) if snippets else "Mentioned in EDGAR filings."

            # Strip parenthetical qualifiers for USGS lookup
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
                "context": context[:500],  # Truncate long snippets
                "severity": severity,
            })

        # Sort by severity (critical first)
        severity_order = {"critical": 0, "high": 1, "moderate": 2, "low": 3, "unknown": 4}
        dependencies.sort(key=lambda d: severity_order.get(d["severity"], 4))

        return json.dumps({
            "company": company_name,
            "minerals_found": minerals_found,
            "dependencies": dependencies,
        })
    finally:
        conn.close()
