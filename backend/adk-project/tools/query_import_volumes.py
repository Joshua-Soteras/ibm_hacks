"""Tool to query import volume data for critical minerals from the database."""

import json
from typing import Optional

from ibm_watsonx_orchestrate.agent_builder.tools import tool

from ._db import get_db_conn


@tool()
def query_import_volumes(mineral_name: str, year: Optional[int] = None) -> str:
    """Query import volumes for a critical mineral, grouped by source country.

    Args:
        mineral_name: Name of the mineral (e.g. gallium, germanium, tungsten, cobalt, rare earths).
        year: Optional year to filter data. If omitted, returns all available years.

    Returns:
        JSON string with {mineral, year, trade_flows} where trade_flows is an
        array of {country, total_value_usd, share_pct} sorted by value descending.
    """
    conn = get_db_conn()
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
    conn.close()

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
            "country": r["country"],
            "total_value_usd": val,
            "share_pct": round(val / total * 100, 2) if total > 0 else 0.0,
        })

    return json.dumps({
        "mineral": mineral_name.lower(),
        "year": year,
        "trade_flows": trade_flows,
    })
