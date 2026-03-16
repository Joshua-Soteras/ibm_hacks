"""Tool to query USITC import volume data for critical minerals."""

import json
from pathlib import Path
from typing import Optional

import pandas as pd
from ibm_watsonx_orchestrate.agent_builder.tools import tool

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "usitc"

MINERAL_FILES = {
    "gallium": "gallium_imports.csv",
    "germanium": "germanium_imports.csv",
    "tungsten": "tungsten_imports.csv",
    "cobalt": "cobalt_imports.csv",
    "rare_earths": "rare_earths_imports.csv",
}


@tool()
def query_import_volumes(mineral_name: str, year: Optional[int] = None) -> str:
    """Query USITC import volumes for a critical mineral, grouped by source country.

    Args:
        mineral_name: Name of the mineral (gallium, germanium, tungsten, cobalt, rare_earths).
        year: Optional year to filter data. If omitted, returns all available years.

    Returns:
        JSON string with an array of {country, total_value_usd, total_quantity_kg, share_pct}
        objects sorted by value descending.
    """
    key = mineral_name.lower().replace(" ", "_")
    filename = MINERAL_FILES.get(key)
    if filename is None:
        return json.dumps({"error": f"Unknown mineral: {mineral_name}. Valid options: {list(MINERAL_FILES.keys())}"})

    csv_path = DATA_DIR / filename
    if not csv_path.exists():
        return json.dumps({"error": f"Data file not found: {csv_path}"})

    df = pd.read_csv(csv_path)
    if df.empty:
        return json.dumps({"mineral": key, "year": year, "trade_flows": [], "note": "No data available yet"})

    if year is not None:
        df = df[df["Year"] == year]

    grouped = (
        df.groupby("Country")
        .agg(total_value_usd=("Import_Value_USD", "sum"), total_quantity_kg=("Import_Quantity_KG", "sum"))
        .reset_index()
        .sort_values("total_value_usd", ascending=False)
    )

    total_value = grouped["total_value_usd"].sum()
    grouped["share_pct"] = round(grouped["total_value_usd"] / total_value * 100, 2) if total_value > 0 else 0.0

    return json.dumps({
        "mineral": key,
        "year": year,
        "trade_flows": grouped.to_dict(orient="records"),
    })
