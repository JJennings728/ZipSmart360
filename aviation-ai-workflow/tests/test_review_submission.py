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
    assert "engineering report" in result["known_missing_documents"]


def test_precheck_detects_missing_section():
    data = {"account": {}, "submission": {}}
    result = MODULE.precheck_submission(data)

    assert result["schema_complete"] is False
    assert "exposures" in result["missing_sections"]
    assert "loss_history" in result["missing_sections"]
    assert "facultative" in result["missing_sections"]


def test_parse_json_output_requires_human_review():
    payload = {
        "submission_readiness": {"status": "review", "summary": "Synthetic test"},
        "missing_information": [],
        "risk_flags": [],
        "fac_review": {"summary": "Synthetic test", "issues": []},
        "recommended_next_action": "Route to human reviewer.",
        "human_review_required": True,
        "limitations": ["Synthetic data only."],
    }

    result = MODULE.parse_json_output(json.dumps(payload))
    assert result["human_review_required"] is True
