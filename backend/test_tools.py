"""Smoke tests for ADK tools against mineralwatch.db."""

import json
import sys
import types
from pathlib import Path

# Mock the ibm_watsonx_orchestrate module so tool imports work without the SDK
mock_orchestrate = types.ModuleType("ibm_watsonx_orchestrate")
mock_agent_builder = types.ModuleType("ibm_watsonx_orchestrate.agent_builder")
mock_tools_mod = types.ModuleType("ibm_watsonx_orchestrate.agent_builder.tools")
mock_tools_mod.tool = lambda *a, **kw: (lambda fn: fn)  # @tool() is a no-op decorator
mock_orchestrate.agent_builder = mock_agent_builder
mock_agent_builder.tools = mock_tools_mod
sys.modules["ibm_watsonx_orchestrate"] = mock_orchestrate
sys.modules["ibm_watsonx_orchestrate.agent_builder"] = mock_agent_builder
sys.modules["ibm_watsonx_orchestrate.agent_builder.tools"] = mock_tools_mod

# Add the adk-project directory to the path so relative imports work
sys.path.insert(0, str(Path(__file__).resolve().parent / "adk-project"))

from tools._db import get_db_conn, strip_mineral_qualifier, USGS_COL, DEFAULT_RISK_SCORE
from tools.query_import_volumes import query_import_volumes
from tools.get_mineral_profile import get_mineral_profile
from tools.extract_mineral_deps import extract_mineral_dependencies
from tools.summarize_risk_section import summarize_risk_section
from tools.compute_composite_risk import compute_composite_risk
from tools.compute_herfindahl import compute_herfindahl

PASS = 0
FAIL = 0


def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}  {detail}")


def test_strip_mineral_qualifier():
    print("\n--- strip_mineral_qualifier ---")
    check("simple name", strip_mineral_qualifier("GALLIUM") == "GALLIUM")
    check("parenthetical", strip_mineral_qualifier("HAFNIUM (see ZIRCONIUM)") == "HAFNIUM")
    check("asterisk", strip_mineral_qualifier("DIAMOND (INDUSTRIAL)*") == "DIAMOND")
    check("trailing star", strip_mineral_qualifier("ARGON*") == "ARGON")
    check("quartz slash", strip_mineral_qualifier("QUARTZ / SILICA") == "QUARTZ / SILICA")


def test_query_import_volumes():
    print("\n--- query_import_volumes ---")
    result = json.loads(query_import_volumes("gallium"))
    check("returns trade_flows", len(result.get("trade_flows", [])) > 0, result)
    check("has country key", "country" in result["trade_flows"][0])
    check("has total_value_usd", "total_value_usd" in result["trade_flows"][0])
    check("has share_pct", "share_pct" in result["trade_flows"][0])
    shares = sum(f["share_pct"] for f in result["trade_flows"])
    check("shares sum to ~100", 99.9 <= shares <= 100.1, f"sum={shares}")

    # Test with year filter
    result_yr = json.loads(query_import_volumes("cobalt", year=2024))
    check("year filter works", result_yr["year"] == 2024)

    # Test unknown mineral
    result_unk = json.loads(query_import_volumes("unobtainium"))
    check("unknown mineral returns empty", result_unk["trade_flows"] == [])


def test_get_mineral_profile():
    print("\n--- get_mineral_profile ---")
    result = json.loads(get_mineral_profile("gallium"))
    check("has mineral", result.get("mineral") == "gallium")
    check("has supply_risk", result.get("supply_risk") != "", result)
    check("has top_producer", result.get("top_producer") != "")
    check("has fab_stage", result.get("fab_stage") != "")
    check("has edgar_hits", "edgar_hits" in result, result)
    check("has blind_spot_assessment", "blind_spot_assessment" in result)

    # Test unknown mineral
    result_unk = json.loads(get_mineral_profile("unobtainium"))
    check("unknown mineral returns error", "error" in result_unk)


def test_extract_mineral_dependencies():
    print("\n--- extract_mineral_dependencies ---")
    result = json.loads(extract_mineral_dependencies("AMD"))
    check("finds AMD", result.get("company") == "AMD")
    check("has minerals_found", len(result.get("minerals_found", [])) > 0, result)
    check("has dependencies", len(result.get("dependencies", [])) > 0)

    dep = result["dependencies"][0]
    check("dep has mineral", "mineral" in dep)
    check("dep has context", "context" in dep)
    check("dep has severity", dep.get("severity") in ("critical", "high", "moderate", "low", "unknown"))

    # Verify sorted by severity
    severity_order = {"critical": 0, "high": 1, "moderate": 2, "low": 3, "unknown": 4}
    severities = [severity_order.get(d["severity"], 4) for d in result["dependencies"]]
    check("sorted by severity", severities == sorted(severities))

    # Test unknown company
    result_unk = json.loads(extract_mineral_dependencies("FakeCompanyXYZ"))
    check("unknown company returns note", "note" in result_unk)


def test_extract_deps_fallback():
    """Test fallback to edgar_filing_details for companies not in the matrix."""
    print("\n--- extract_mineral_dependencies (fallback) ---")
    result = json.loads(extract_mineral_dependencies("Intel"))
    check("finds Intel", result.get("company") == "Intel")
    check("has minerals_found", len(result.get("minerals_found", [])) > 0,
          f"got: {result.get('minerals_found', [])}")
    check("has dependencies", len(result.get("dependencies", [])) > 0)
    check("uses filing_details source", result.get("source") == "edgar_filing_details",
          f"got: {result.get('source')}")

    if result.get("dependencies"):
        dep = result["dependencies"][0]
        check("fallback dep has severity",
              dep.get("severity") in ("critical", "high", "moderate", "low", "unknown"))


def test_extract_mineral_deps_parenthetical():
    """Test that minerals with parenthetical names still get USGS severity."""
    print("\n--- extract_mineral_dependencies (parenthetical minerals) ---")
    # Find a company that has HAFNIUM or DIAMOND exposure
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT "Company / Mineral" FROM edgar_mineral_company_matrix '
        'WHERE "HAFNIUM (see ZIRCONIUM)" IS NOT NULL AND "HAFNIUM (see ZIRCONIUM)" != 0 LIMIT 1'
    )
    row = cursor.fetchone()
    conn.close()

    if row:
        # Use first few words of company name for LIKE matching
        company = row["Company / Mineral"].split("(")[0].strip()
        result = json.loads(extract_mineral_dependencies(company))
        hafnium_deps = [d for d in result.get("dependencies", []) if "HAFNIUM" in d["mineral"]]
        if hafnium_deps:
            check("HAFNIUM severity not unknown", hafnium_deps[0]["severity"] != "unknown",
                  f"got: {hafnium_deps[0]['severity']}")
        else:
            check("HAFNIUM found in deps", False, "HAFNIUM not in dependencies list")
    else:
        print("  SKIP  No company with HAFNIUM exposure in matrix")


def test_summarize_risk_section():
    print("\n--- summarize_risk_section ---")
    result = json.loads(summarize_risk_section("AMD"))
    check("has company", result.get("company") == "AMD")
    check("has risk_summary", len(result.get("risk_summary", "")) > 0)
    check("has exposure_score", 0 <= result.get("exposure_score", -1) <= 100, result)
    check("has key_risks", len(result.get("key_risks", [])) > 0)
    # Verify EDGAR hits enrichment is included
    has_hits = any("EDGAR hits" in kr for kr in result.get("key_risks", []))
    check("key_risks include EDGAR hits", has_hits, result.get("key_risks", [])[:2])

    # Test unknown company
    result_unk = json.loads(summarize_risk_section("FakeCompanyXYZ"))
    check("unknown company score=0", result_unk.get("exposure_score") == 0)


def test_summarize_mineral_mode():
    """Test mineral-centric mode of summarize_risk_section."""
    print("\n--- summarize_risk_section (mineral-centric) ---")
    result = json.loads(summarize_risk_section("", mineral_name="GALLIUM"))
    check("has mineral", result.get("mineral") == "GALLIUM")
    check("mode is mineral_centric", result.get("mode") == "mineral_centric")
    check("has exposure_score", result.get("exposure_score", 0) > 0,
          f"got: {result.get('exposure_score')}")
    check("has company_count", result.get("company_count", 0) > 0,
          f"got: {result.get('company_count')}")
    check("has supply_risk", result.get("supply_risk") == "CRITICAL",
          f"got: {result.get('supply_risk')}")
    check("has key_risks", len(result.get("key_risks", [])) > 0)


def test_compute_herfindahl():
    print("\n--- compute_herfindahl ---")
    trade_result = query_import_volumes("tungsten")
    result = json.loads(compute_herfindahl(trade_result))
    check("has hhi", "hhi" in result)
    check("hhi is positive", result["hhi"] > 0)
    check("has concentration_level", result.get("concentration_level") in ("low", "moderate", "high"))
    check("has top_supplier", result.get("top_supplier") != "unknown")


def test_compute_composite_risk():
    print("\n--- compute_composite_risk ---")
    trade_json = json.dumps({"hhi": 5000, "concentration_level": "high"})
    corp_json = json.dumps({"exposure_score": 70})
    result = json.loads(compute_composite_risk(trade_json, corp_json, mineral_name="gallium"))
    check("has composite_score", "composite_score" in result)
    check("has risk_level", result.get("risk_level") in ("low", "medium", "high", "critical"))
    check("has breakdown", "breakdown" in result)
    # With gallium (CRITICAL supply risk -> 90), substitutability should be 90
    check("substitutability from DB", result["breakdown"]["substitutability_risk"] == 90,
          f"got: {result['breakdown']['substitutability_risk']}")
    # HHI 5000 now normalizes to 85.0 (piecewise), not 50.0
    check("trade_risk piecewise", result["breakdown"]["trade_risk"] == 85.0,
          f"got: {result['breakdown']['trade_risk']}")

    # Test without mineral_name (should use default)
    result3 = json.loads(compute_composite_risk(trade_json, corp_json))
    check("default substitutability", result3["breakdown"]["substitutability_risk"] == DEFAULT_RISK_SCORE,
          f"got: {result3['breakdown']['substitutability_risk']}")


def test_end_to_end_pipeline():
    """Simulate the full orchestrator pipeline for a mineral."""
    print("\n--- end-to-end pipeline (gallium) ---")
    # Step 1: trade_intel_agent gets trade data
    trade_result = query_import_volumes("gallium")
    trade_data = json.loads(trade_result)
    check("e2e: trade flows found", len(trade_data["trade_flows"]) > 0)

    # Step 2: compute HHI
    hhi_result = compute_herfindahl(trade_result)
    hhi_data = json.loads(hhi_result)
    check("e2e: HHI computed", hhi_data["hhi"] > 0)

    # Step 3: corporate_exposure_agent analyzes a company
    corp_result = summarize_risk_section("AMD")
    corp_data = json.loads(corp_result)
    check("e2e: corporate score", corp_data["exposure_score"] > 0)

    # Step 4: orchestrator computes composite risk
    composite_result = compute_composite_risk(hhi_result, corp_result, mineral_name="gallium")
    composite_data = json.loads(composite_result)
    check("e2e: composite score", composite_data["composite_score"] > 0)
    check("e2e: risk level set", composite_data["risk_level"] in ("low", "medium", "high", "critical"))
    # With piecewise HHI normalization, gallium composite should be in 70-85 range
    check("e2e: gallium score 70-85", 70 <= composite_data["composite_score"] <= 85,
          f"got: {composite_data['composite_score']}")
    print(f"  INFO  composite_score={composite_data['composite_score']}, "
          f"risk_level={composite_data['risk_level']}")


if __name__ == "__main__":
    test_strip_mineral_qualifier()
    test_query_import_volumes()
    test_get_mineral_profile()
    test_extract_mineral_dependencies()
    test_extract_deps_fallback()
    test_extract_mineral_deps_parenthetical()
    test_summarize_risk_section()
    test_summarize_mineral_mode()
    test_compute_herfindahl()
    test_compute_composite_risk()
    test_end_to_end_pipeline()

    print(f"\n{'='*40}")
    print(f"Results: {PASS} passed, {FAIL} failed")
    if FAIL > 0:
        sys.exit(1)
