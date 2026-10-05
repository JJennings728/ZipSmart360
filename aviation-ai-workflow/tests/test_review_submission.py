import importlib.util
import json
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "src" / "review_submission.py"
SPEC = importlib.util.spec_from_file_location("review_submission", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


SAMPLE_PATH = Path(__file__).parents[1] / "sample-data" / "synthetic_submission.json"


def test_synthetic_submission_has_required_sections():
    data = MODULE.load_submission(SAMPLE_PATH)
    result = MODULE.precheck_submission(data)

    assert result["schema_complete"] is True
    assert result["missing_sections"] == []
    assert "updated aircraft valuation support" in result["known_missing_documents"]
    assert "pilot 27 recurrent training record" in result["known_missing_documents"]
    assert "detailed caribbean operations breakdown" in result["known_missing_documents"]

    assert data["exposures"]["operator_profile"]["aircraft_count"] == 28
    assert data["exposures"]["hull"]["total_hull_value_usd"] == 436000000


def test_precheck_detects_missing_section():
    data = {"account": {}, "submission": {}}
    result = MODULE.precheck_submission(data)

    assert result["schema_complete"] is False
    assert "exposures" in result["missing_sections"]
    assert "loss_history" in result["missing_sections"]
    assert "delegated_authority" in result["missing_sections"]
    assert "facultative" in result["missing_sections"]


def test_parse_json_output_requires_human_review():
    payload = {
        "submission_readiness": {"status": "review", "summary": "Synthetic test"},
        "exposure_summary": {
            "aircraft_count": 28,
            "total_hull_value_usd": 436000000,
            "largest_single_aircraft_hull_usd": 55000000,
            "requested_liability_limit_usd": 500000000,
            "projected_flight_hours": 11500,
            "utilization_change_percent": 29.2,
            "summary": "Synthetic test",
        },
        "hull_asset_analysis": {
            "status": "review_required",
            "summary": "Synthetic test",
            "issues": [],
        },
        "missing_information": [],
        "risk_flags": [],
        "delegated_authority_review": {
            "status": "carrier_referral_indicated",
            "summary": "Synthetic test",
            "reasons": [],
            "disclaimer": "Illustrative only.",
        },
        "fac_review": {"summary": "Synthetic test", "issues": []},
        "recommended_next_action": "Route to human reviewer.",
        "human_review_required": True,
        "limitations": ["Synthetic data only."],
    }

    result = MODULE.parse_json_output(json.dumps(payload))
    assert result["human_review_required"] is True



AIRLINE_SAMPLE_PATH = Path(__file__).parents[1] / "sample-data" / "synthetic_airline_submission.json"


def test_large_airline_schedule_is_compacted_for_model_prompt():
    data = MODULE.load_submission(AIRLINE_SAMPLE_PATH)
    compacted = MODULE.compact_for_prompt(data)

    schedule = compacted["exposures"]["aircraft_schedule"]
    assert schedule["record_count"] == 1050
    assert schedule["truncated_for_ai_prompt"] is True
    assert len(schedule["sample"]) == 5

    # The original submission remains complete for deterministic reconciliation.
    assert len(data["exposures"]["aircraft_schedule"]) == 1050
