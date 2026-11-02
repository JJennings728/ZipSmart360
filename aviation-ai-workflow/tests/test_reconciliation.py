import importlib.util
import json
from pathlib import Path


BASE = Path(__file__).parents[1]
MODULE_PATH = BASE / "src" / "reconciliation.py"
SPEC = importlib.util.spec_from_file_location("reconciliation", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)

SUBMISSION_PATH = BASE / "sample-data" / "synthetic_submission.json"
EVIDENCE_PATH = BASE / "sample-data" / "synthetic_evidence.json"


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def test_synthetic_reconciliation_detects_known_ground_truth():
    submission = load_json(SUBMISSION_PATH)
    evidence = load_json(EVIDENCE_PATH)

    result = MODULE.reconcile_case(submission, evidence)

    assert result["status"] == "REVIEW_REQUIRED"
    assert result["summary"]["source_count"] == 6
    assert result["summary"]["check_count"] == 13
    assert result["summary"]["verified_count"] == 6
    assert result["summary"]["exception_count"] == 7
    assert result["summary"]["aircraft_total"] == 28
    assert result["summary"]["aircraft_reconciled_to_certificate"] == 27

    evaluation = result["evaluation"]
    assert evaluation["ground_truth_available"] is True
    assert evaluation["expected_exception_count"] == 7
    assert evaluation["detected_expected_count"] == 7
    assert evaluation["detection_rate_percent"] == 100.0
    assert evaluation["missed_expected_rule_ids"] == []
    assert evaluation["unexpected_exception_rule_ids"] == []


def test_exception_statuses_are_conservative_and_traceable():
    submission = load_json(SUBMISSION_PATH)
    evidence = load_json(EVIDENCE_PATH)

    result = MODULE.reconcile_case(submission, evidence)
    by_rule = {item["rule_id"]: item for item in result["exceptions"]}

    assert by_rule["R-020"]["result_status"] == "REFER"
    assert by_rule["R-030"]["result_status"] == "MISMATCH"
    assert by_rule["R-031"]["result_status"] == "MISMATCH"
    assert by_rule["R-041"]["result_status"] == "MISSING_EVIDENCE"
    assert by_rule["R-054"]["result_status"] == "UNRESOLVED"
    assert by_rule["R-060"]["result_status"] == "MISSING_EVIDENCE"
    assert by_rule["R-070"]["result_status"] == "REFER"

    for exception in result["exceptions"]:
        assert exception["evidence"]
        assert exception["status"] == "OPEN"


def test_external_event_is_not_automatically_called_an_undisclosed_loss():
    submission = load_json(SUBMISSION_PATH)
    evidence = load_json(EVIDENCE_PATH)

    result = MODULE.reconcile_case(submission, evidence)
    event_exception = next(
        item for item in result["exceptions"] if item["rule_id"] == "R-054"
    )

    assert "not reconciled" in event_exception["summary"].lower()
    assert "do not label it an undisclosed loss" in event_exception["suggested_action"].lower()


AIRLINE_SUBMISSION_PATH = BASE / "sample-data" / "synthetic_airline_submission.json"
AIRLINE_EVIDENCE_PATH = BASE / "sample-data" / "synthetic_airline_evidence.json"


def test_major_airline_case_reconciles_1050_aircraft_and_detects_answer_key():
    submission = load_json(AIRLINE_SUBMISSION_PATH)
    evidence = load_json(AIRLINE_EVIDENCE_PATH)

    result = MODULE.reconcile_case(submission, evidence)

    assert result["status"] == "REVIEW_REQUIRED"
    assert result["summary"]["source_count"] == 8
    assert result["summary"]["check_count"] == 14
    assert result["summary"]["verified_count"] == 6
    assert result["summary"]["exception_count"] == 8
    assert result["summary"]["aircraft_total"] == 1050
    assert result["summary"]["aircraft_reconciled_to_certificate"] == 1049

    evaluation = result["evaluation"]
    assert evaluation["ground_truth_available"] is True
    assert evaluation["expected_exception_count"] == 8
    assert evaluation["detected_expected_count"] == 8
    assert evaluation["detection_rate_percent"] == 100.0
    assert evaluation["missed_expected_rule_ids"] == []
    assert evaluation["unexpected_exception_rule_ids"] == []

    event_link_check = next(item for item in result["checks"] if item["rule_id"] == "R-050")
    assert event_link_check["evidence"][0]["source_id"] == "EVT-A1"


def test_major_airline_delivery_plan_is_evidence_backed_mismatch():
    submission = load_json(AIRLINE_SUBMISSION_PATH)
    evidence = load_json(AIRLINE_EVIDENCE_PATH)

    result = MODULE.reconcile_case(submission, evidence)
    delivery_check = next(item for item in result["checks"] if item["rule_id"] == "R-081")

    assert delivery_check["status"] == "MISMATCH"
    assert "90 expected deliveries" in delivery_check["summary"]
    assert "87" in delivery_check["summary"]
