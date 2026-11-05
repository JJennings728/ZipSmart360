"""Print an internal case brief from a reconciled synthetic Power BI export.

python -m src.aerocie.submission_brief --export-dir PATH --submission-id S007
"""
import argparse
import csv
import json
from pathlib import Path

from .export_reconciliation import reconcile

QUESTIONS = {
    "MRO_COVERAGE_MISSING": "Which dated maintenance observations cover this aircraft model?",
    "ANNUAL_FLIGHT_HOURS_MISSING": "What annual utilization and reporting period can the operator document?",
    "LOSS_HISTORY_MISSING": "What five-year loss history can the operator provide?",
    "PILOT_EVIDENCE_MISSING": "What records document the assigned pilot's total and make/model hours?",
    "RECURRENT_TRAINING_MISSING": "When was recurrent training completed, and which record supports it?",
}


def lookup(folder, table, field, value):
    with (folder / f"{table}.csv").open(encoding="utf-8-sig", newline="") as stream:
        matches = [row for row in csv.DictReader(stream) if row[field] == value]
    if len(matches) != 1:
        raise ValueError(f"Expected one {field}={value!r} in {table}, found {len(matches)}")
    return matches[0]


def build_brief(folder: Path, submission_id: str) -> str:
    reconcile(folder)
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    required = {"v_submission_triage", "submission_quality", "source_registry", "v_severity_scenarios"}
    if required.difference(entry["view"] for entry in manifest["tables"]):
        raise ValueError("Required report input missing from digest manifest")
    case = lookup(folder, "v_submission_triage", "submission_id", submission_id)
    quality = lookup(folder, "submission_quality", "submission_id", submission_id)
    source = lookup(folder, "source_registry", "source_id", case["submission_source_id"])
    if source["is_synthetic"] != "1" or source["license_status"] != "SYNTHETIC_ONLY":
        raise ValueError("Expected a synthetic intake source")
    lines = [
        f"AeroCIE submission review | {submission_id}",
        "Synthetic demonstration | Internal human review only",
        "",
        f"Aircraft: {case['manufacturer']} {case['model']} | {case['registration']}",
        f"Operation: {case['operation_type']} | Submitted: {case['submitted_on']}",
        f"Requested hull (USD): {case['requested_hull_value_usd'] or 'Unknown'}",
        f"Demo triage label: {case['triage_recommendation']}",
        f"Quality status: {quality['quality_status']}",
        "",
        "Evidence follow-up",
    ]
    for issue in filter(None, quality["issue_codes"].split(";")):
        question = QUESTIONS.get(issue, "Which supporting record resolves this flagged issue?")
        lines.append(f"- {issue}: {question}")
    if not quality["issue_codes"]:
        lines.append("No issues flagged by the synthetic checks. Review supporting records.")
    lines.extend([
        "",
        f"Intake source: {source['source_id']} | {source['provider']} | As of {source['source_as_of']}",
        f"Intake snapshot SHA-256: {source['payload_sha256']}",
    ])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-dir", required=True, type=Path)
    parser.add_argument("--submission-id", required=True)
    args = parser.parse_args()
    try:
        brief = build_brief(args.export_dir, args.submission_id)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"Cannot generate brief: {error}\n")
    print(brief)


if __name__ == "__main__":
    main()
