"""Static safety checks for the SRP-branded AeroCIE four-page PBIR report.

These assertions do NOT replace Desktop rendering, refresh or DAX execution.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "powerbi" / "AeroCIE-Underwriting.Report"
MODEL = ROOT / "powerbi" / "AeroCIE-Underwriting.SemanticModel"
DEFINITION = REPORT / "definition"
EXPECTED_PAGES = ("Overview", "RiskAnalysis", "MROSeverity", "EvidenceQuality")


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _visuals(page: str) -> list[dict]:
    files = sorted((DEFINITION / "pages" / page / "visuals").glob("*/visual.json"))
    assert files, f"{page} has no visuals"
    return [_read(path) for path in files]


def test_four_pages_registered_with_live_visuals() -> None:
    metadata = _read(DEFINITION / "pages" / "pages.json")
    assert tuple(metadata["pageOrder"]) == EXPECTED_PAGES
    assert metadata["activePageName"] == "Overview"
    report_visuals = sum(len(_visuals(p)) for p in EXPECTED_PAGES)
    assert report_visuals >= 50
    for page in EXPECTED_PAGES:
        page_def = _read(DEFINITION / "pages" / page / "page.json")
        assert page_def["width"] == 1280
        assert page_def["height"] == 720
        for visual in _visuals(page):
            pos = visual["position"]
            assert pos["x"] >= 0 and pos["y"] >= 0
            assert pos["x"] + pos["width"] <= 1280
            assert pos["y"] + pos["height"] <= 720


def test_model_bound_visuals_reference_declared_fields() -> None:
    expected_tables = {
        "v_submission_triage", "v_submission_features", "v_mro_latest",
        "v_severity_scenarios", "submission_quality", "source_registry",
    }
    model_text = {
        name: (MODEL / "definition" / "tables" / (name + ".tmdl")).read_text(encoding="utf-8")
        for name in expected_tables
    }
    bound = 0
    for page in EXPECTED_PAGES:
        for visual in _visuals(page):
            for role in visual["visual"].get("query", {}).get("queryState", {}).values():
                for projection in role.get("projections", []):
                    fld = projection["field"]
                    kind = "Measure" if "Measure" in fld else "Column"
                    entity = fld[kind]["Expression"]["SourceRef"]["Entity"]
                    prop = fld[kind]["Property"]
                    assert entity in model_text, f"Unknown entity: {entity}"
                    text = model_text[entity]
                    if kind == "Measure":
                        assert ("measure '" + prop + "'") in text or ("measure " + prop + " =") in text, (entity, prop)
                    else:
                        assert ("column " + prop + "\\n") in text, (entity, prop)
                    bound += 1
    assert bound >= 55


def test_image_resources_are_real_files_and_registered() -> None:
    report = _read(DEFINITION / "report.json")
    resources = {
        item["name"]: item
        for package in report.get("resourcePackages", [])
        if package["name"] == "RegisteredResources"
        for item in package["items"]
    }
    assert resources["SRP-AeroCIE-2026.json"]["type"] == "CustomTheme"
    images = [name for name, item in resources.items() if item["type"] == "Image"]
    assert len(images) == 4
    for name in images:
        content = (REPORT / "StaticResources" / "RegisteredResources" / name).read_bytes()
        assert content[:3] == b"\\xff\\xd8\\xff", f"Not JPEG: {name}"
    names_in_use = set()
    for page in EXPECTED_PAGES:
        for visual in _visuals(page):
            if visual["visual"]["visualType"] == "image":
                for general in visual["visual"].get("objects", {}).get("general", []):
                    item = general["properties"]["imageUrl"]["expr"]["ResourcePackageItem"]["ItemName"]
                    assert item in images
                    names_in_use.add(item)
    assert names_in_use.issubset(set(images))\n    assert "srp-licensed-stock-engine.jpg" in names_in_use


def test_research_only_status_is_visible_everywhere() -> None:
    for page in EXPECTED_PAGES:
        contents = json.dumps(_visuals(page)).upper()
        assert "SYNTHETIC INTERNAL DEMONSTRATION" in contents
        assert "NO QUOTING, BINDING" in contents
    assert "REQUESTED HULL" in json.dumps(_visuals("Overview")).upper()
    assert "EVIDENCE" in json.dumps(_visuals("EvidenceQuality")).upper()
