"""Offline consistency gate for the synthetic AeroCIE Power BI CSV handoff.

Read-only; validates export manifest, per-file digests, joins and totals.
No claim calibration, premium analysis or licensing authorization is implied.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import sys


def _rows(root: Path, name: str, required: set[str]) -> list[dict[str, str]]:
    path = root / name
    if not path.is_file():
        raise ValueError(f"Missing export: {name}")
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not required.issubset(set(reader.fieldnames or ())):
            raise ValueError(f"Missing expected columns: {name}")
        rows = list(reader)
    ids = [row["submission_id"] for row in rows]
    if not ids or len(ids) != len(set(ids)) or any(not item for item in ids):
        raise ValueError(f"Empty or duplicate submission identifiers: {name}")
    return rows


def _num(value: str) -> Decimal | None:
    if value is None or not value.strip():
        return None
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"Invalid numeric data: {value!r}") from exc
    if not number.is_finite():
        raise ValueError("Nonfinite number in export")
    return number


def reconcile(folder: Path) -> dict:
    root = folder.resolve()
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    audit = json.loads((root / "quality_audit.json").read_text(encoding="utf-8"))
    if (manifest.get("data_mode") != "SYNTHETIC_ONLY" or
        manifest.get("authority") != "UNDERWRITER_REVIEW_REQUIRED" or
        manifest.get("quality_gate") != "INTERNAL_DEMO_ONLY" or
        audit.get("quality_gate") != "INTERNAL_DEMO_ONLY" or
        audit.get("external_release_authorized") is not False):
        raise ValueError("Export not approved for synthetic internal reconciliation")

    manifest_tables = manifest.get("tables", [])
    if not manifest_tables:
        raise ValueError("Missing manifest table entries")
    for entry in manifest_tables:
        name = entry["view"]
        if not name.isidentifier():
            raise ValueError("Unexpected manifest view name")
        file = root / f"{name}.csv"
        if not file.is_file():
            raise ValueError(f"Missing manifest file: {name}")
        digest = hashlib.sha256(file.read_bytes()).hexdigest()
        if digest != entry["sha256"]:
            raise ValueError(f"CSV digest mismatch: {name}")

    triage = _rows(root, "v_submission_triage.csv",
                   {"submission_id", "triage_recommendation", "risk_points",
                    "insufficient_evidence", "requested_hull_value_usd"})
    quality = _rows(root, "submission_quality.csv",
                    {"submission_id", "research_label", "risk_points", "quality_status", "issue_codes"})
    severity = _rows(root, "v_severity_scenarios.csv",
                     {"submission_id", "scenario_low_usd", "scenario_base_usd",
                      "scenario_high_usd", "triage_recommendation"})
    by_quality = {r["submission_id"]: r for r in quality}
    by_severity = {r["submission_id"]: r for r in severity}
    ids = {r["submission_id"] for r in triage}
    if ids != set(by_quality) or ids != set(by_severity):
        raise ValueError("Submission ID mismatch across export tables")

    counts = Counter()
    hull_total = Decimal(0)
    scenario_totals = [Decimal(0), Decimal(0), Decimal(0)]
    for row in triage:
        key = row["submission_id"]
        label = row["triage_recommendation"]
        q = by_quality[key]
        s = by_severity[key]
        if label not in {"Quote", "Refer", "Decline"} or label != q["research_label"] or label != s["triage_recommendation"]:
            raise ValueError(f"Triage label disagreement: {key}")
        if _num(row["risk_points"]) != _num(q["risk_points"]):
            raise ValueError(f"Risk score disagreement: {key}")
        counts[label] += 1
        hull_total += _num(row["requested_hull_value_usd"]) or Decimal(0)
        scenarios = [_num(s[column]) for column in
                     ("scenario_low_usd", "scenario_base_usd", "scenario_high_usd")]
        if all(item is None for item in scenarios):
            continue
        if any(item is None for item in scenarios) or not (Decimal(0) <= scenarios[0] <= scenarios[1] <= scenarios[2]):
            raise ValueError(f"Invalid scenario sensitivity: {key}")
        if row["insufficient_evidence"] == "1":
            raise ValueError(f"Scenario provided despite insufficient evidence: {key}")
        for index, value in enumerate(scenarios):
            scenario_totals[index] += value

    return {
        "status": "PASS",
        "scope": "SYNTHETIC_INTERNAL_ONLY",
        "submission_count": len(triage),
        "labels": dict(sorted(counts.items())),
        "requested_hull_total_usd_NOT_INSURED_VALUE": str(hull_total),
        "scenario_totals_usd_NOT_CLAIM_FORECAST": [str(v) for v in scenario_totals],
        "files_verified_by_sha256": len(manifest_tables),
        "release_authorized": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = reconcile(args.export_dir)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        print(f"RECONCILIATION FAILED: {error}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
