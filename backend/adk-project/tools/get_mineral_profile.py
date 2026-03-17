"""Tool to retrieve a mineral profile from the mineralwatch database."""

import json
from urllib.parse import quote

from ibm_watsonx_orchestrate.agent_builder.tools import tool

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent))
from _api import is_api_mode, api_get, BACKEND_CONNECTION
from _db import get_db_conn, USGS_COL


def _via_api(mineral_name: str) -> str:
    try:
        data = api_get(f"/api/mineral/profile/{quote(mineral_name, safe='')}")
        return json.dumps(data)
    except Exception as e:
        return json.dumps({"error": f"Backend API unavailable: {e}"})


def _via_db(mineral_name: str) -> str:
    conn = get_db_conn()
    try:
        cursor = conn.cursor()

        cursor.execute(
            f'SELECT * FROM usgs_minerals WHERE "{USGS_COL}" LIKE ?',
            (f"%{mineral_name}%",),
        )
        rows = cursor.fetchall()

        if not rows:
            return json.dumps({"error": f"Mineral '{mineral_name}' not found in USGS data."})

        row = rows[0]
        cols = [desc[0] for desc in cursor.description]
        usgs_data = dict(zip(cols, row))

        COL_MATERIAL = "Material / Compound\nUsed in Fab"
        COL_FUNCTION = "What It Does in the Chip"
        COL_CRITICAL = "Critical Mineral?\n(2025 List)"
        COL_PRODUCER = "Top Producer\n(Country)"
        COL_HTS = "HTS Code\n(USITC DataWeb)"

        profile = {
            "mineral": mineral_name.lower(),
            "fab_stage": usgs_data.get("Fab Stage", ""),
            "material_compound": usgs_data.get(COL_MATERIAL, ""),
            "chip_function": usgs_data.get(COL_FUNCTION, ""),
            "critical_mineral": usgs_data.get(COL_CRITICAL, ""),
            "top_producer": usgs_data.get(COL_PRODUCER, ""),
            "supply_risk": usgs_data.get("Supply Risk", ""),
            "hts_code": usgs_data.get(COL_HTS, ""),
        }

        if len(rows) > 1:
            profile["additional_uses"] = []
            for r in rows[1:]:
                d = dict(zip(cols, r))
                profile["additional_uses"].append({
                    "fab_stage": d.get("Fab Stage", ""),
                    "material_compound": d.get(COL_MATERIAL, ""),
                    "chip_function": d.get(COL_FUNCTION, ""),
                })

        cursor.execute(
            'SELECT * FROM edgar_summary WHERE Mineral LIKE ?',
            (f"%{mineral_name}%",),
        )
        edgar_row = cursor.fetchone()
        if edgar_row:
            edgar_cols = [desc[0] for desc in cursor.description]
            edgar_data = dict(zip(edgar_cols, edgar_row))
            profile["edgar_hits"] = edgar_data.get("EDGAR Hits", 0)
            profile["unique_companies"] = edgar_data.get("Unique\nCompanies", 0)
            profile["edgar_risk_alignment"] = edgar_data.get("EDGAR vs Risk\nAlignment", "")

        cursor.execute(
            'SELECT * FROM edgar_blind_spot_analysis WHERE Mineral LIKE ?',
            (f"%{mineral_name}%",),
        )
        blind_row = cursor.fetchone()
        if blind_row:
            blind_cols = [desc[0] for desc in cursor.description]
            blind_data = dict(zip(blind_cols, blind_row))
            profile["blind_spot_assessment"] = blind_data.get("Assessment", "")
            profile["recommended_action"] = blind_data.get("Action", "")

        return json.dumps(profile)
    finally:
        conn.close()


@tool(expected_credentials=[BACKEND_CONNECTION])
def get_mineral_profile(mineral_name: str) -> str:
    """Retrieve a structured profile for a critical mineral from USGS data.

    Queries the mineralwatch database for USGS mineral data, EDGAR filing
    summary, and blind-spot analysis to return a comprehensive mineral profile.

    Args:
        mineral_name: Name of the mineral (e.g. gallium, germanium, tungsten, cobalt, rare earths).

    Returns:
        JSON string with mineral profile including production, supply risk,
        EDGAR coverage, and blind-spot assessment.
    """
    if is_api_mode():
        return _via_api(mineral_name)
    return _via_db(mineral_name)
