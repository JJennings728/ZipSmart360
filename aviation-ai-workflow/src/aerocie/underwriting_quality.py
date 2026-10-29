"""AeroCIE underwriting evidence and model quality audit.

Read-only checks reconcile locally imported synthetic source rows to their
SHA-256 records, then explain missing or inconsistent submission inputs.
This is an integrity and quality check, never a verification of third-party
source authority, predictive accuracy or permission to bind coverage.
"""
from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
from typing import Any

from . import underwriting_pipeline

SCHEMA = "AEROCIE-UW-QUALITY-AUDIT-v1"
# Column order must equal the fixed insertion order used in underwriting_pipeline.
SOURCE_TABLES: dict[str, tuple[str, tuple[str, ...]]] = {
    "MRO": ("fact_mro_constraints", (
        "constraint_id", "facility_id", "manufacturer", "model", "as_of",
        "repair_wait_days", "parts_availability_index", "parts_cost_index", "source_id")),
    "INTAKE": ("fact_underwriting_submissions", (
        "submission_id", "submitted_on", "aircraft_id", "pilot_id", "operation_type",
        "annual_flight_hours", "losses_last_five_years", "requested_hull_value_usd", "source_id")),
    "NTSB": ("fact_ntsb_model_context", (
        "context_id", "manufacturer", "model", "period_start", "period_end",
        "event_count", "denominator_flight_hours", "source_id")),
    "SWIM": ("fact_swim_operations", (
        "observation_id", "manufacturer", "model", "period_start", "period_end",
        "operations_count", "source_id")),
}


def _iso_date(raw: object) -> date | None:
    if not isinstance(raw, str) or len(raw) != 10:
        return None
    try:
        parsed = date.fromisoformat(raw)
    except ValueError:
        return None
    return parsed if parsed.isoformat() == raw else None


def _source_checks(con: sqlite3.Connection) -> list[dict]:
    checks = []
    registry = {r["source_id"]: dict(r) for r in con.execute(
        "SELECT source_id,source_as_of,payload_sha256,license_status,is_synthetic "
        "FROM source_registry")}
    expected = {f"SRC-{kind}" for kind in SOURCE_TABLES}
    for kind, (table, columns) in SOURCE_TABLES.items():
        key = f"SRC-{kind}"
        rec = registry.get(key)
        safe_columns = ", ".join(columns)
        rows = [tuple(r) for r in con.execute(
            f"SELECT {safe_columns} FROM {table} WHERE source_id = ? ORDER BY rowid", (key,))]
        digest = underwriting_pipeline._hash({"data": rows, "kind": kind,
                                               "version": underwriting_pipeline.VERSION})
        expected_digest = rec["payload_sha256"] if rec else None
        issues = []
        if rec is None:
            issues.append("SOURCE_REGISTRY_MISSING")
        else:
            if rec["is_synthetic"] != 1 or rec["license_status"] != "SYNTHETIC_ONLY":
                issues.append("UNEXPECTED_SOURCE_MODE")
            if expected_digest != digest:
                issues.append("SOURCE_FINGERPRINT_MISMATCH")
            if _iso_date(rec["source_as_of"]) is None:
                issues.append("SOURCE_DATE_INVALID")
        foreign_rows = con.execute(
            f"SELECT COUNT(*) FROM {table} WHERE source_id != ?", (key,)).fetchone()[0]
        if foreign_rows:
            issues.append("UNEXPECTED_SOURCE_ID")
        if not rows:
            issues.append("SOURCE_EMPTY")
        checks.append({"source_id": key, "dataset": kind, "rows": len(rows),
                       "local_fingerprint": digest, "registered_fingerprint": expected_digest,
                       "status": "FINGERPRINT_MATCH_ONLY" if not issues else "BLOCKED",
                       "issues": issues})
    if set(registry) != expected:
        checks.append({"source_id": "UNEXPECTED_REGISTRY_ENTRIES", "dataset": "OTHER",
                       "rows": 0, "status": "BLOCKED", "issues": ["SOURCE_REGISTRY_SET_CHANGED"]})
    return checks


DIMENSION_TABLES: dict[str, tuple[str, ...]] = {
    "dim_aircraft": ("aircraft_id", "registration", "manufacturer", "model", "category",
                     "year_built", "composite_material_flag"),
    "dim_pilot": ("pilot_id", "certificate_level", "total_flight_hours", "make_model_hours",
                  "recurrent_training_verified"),
    "dim_mro_facility": ("facility_id", "name", "region", "country_code"),
    "source_registry": ("source_id", "provider", "dataset_name", "source_url",
                        "source_as_of", "retrieved_at", "payload_sha256",
                        "license_status", "is_synthetic"),
    "model_policy": ("policy_id", "policy_version", "quote_max_risk_points",
                     "decline_review_min_risk_points", "approved_for_automatic_binding", "note"),
}


def _dimension_checks(con: sqlite3.Connection) -> list[dict]:
    records = {row["dataset_name"]: row["payload_sha256"] for row in con.execute(
        "SELECT dataset_name, payload_sha256 FROM dataset_integrity")}
    results = []
    for name, columns in DIMENSION_TABLES.items():
        rows = [tuple(r) for r in con.execute(
            f"SELECT {', '.join(columns)} FROM {name} ORDER BY rowid")]
        digest = underwriting_pipeline._hash({"data": rows, "kind": name,
                                                "version": underwriting_pipeline.VERSION})
        issues = []
        if name not in records:
            issues.append("DIMENSION_FINGERPRINT_MISSING")
        elif records[name] != digest:
            issues.append("DIMENSION_FINGERPRINT_MISMATCH")
        if not rows:
            issues.append("DIMENSION_EMPTY")
        results.append({"dataset": name, "rows": len(rows), "local_fingerprint": digest,
                        "registered_fingerprint": records.get(name),
                        "status": "FINGERPRINT_MATCH_ONLY" if not issues else "BLOCKED",
                        "issues": issues})
    if set(records) != set(DIMENSION_TABLES):
        results.append({"dataset": "UNEXPECTED_DIMENSION_ENTRIES", "rows": 0,
                        "status": "BLOCKED", "issues": ["DIMENSION_REGISTRY_SET_CHANGED"]})
    return results


def _policy_check(con: sqlite3.Connection) -> dict:
    policies = [dict(r) for r in con.execute(
        "SELECT policy_id,policy_version,quote_max_risk_points,decline_review_min_risk_points,"
        "approved_for_automatic_binding FROM model_policy")]
    safe = (len(policies) == 1 and policies[0]["policy_id"] == "SYNTHETIC_V1" and
            policies[0]["policy_version"] == underwriting_pipeline.VERSION and
            policies[0]["quote_max_risk_points"] == 25 and
            policies[0]["decline_review_min_risk_points"] == 70 and
            policies[0]["approved_for_automatic_binding"] == 0)
    return {"status": "EXPECTED_SYNTHETIC_POLICY" if safe else "BLOCKED",
            "policy_version": policies[0]["policy_version"] if len(policies) == 1 else None,
            "issues": [] if safe else ["MODEL_POLICY_CHANGED_WITHOUT_VALIDATION"]}


def _submission_check(row: sqlite3.Row, *, source_integrity_ok: bool,
                      policy_ok: bool) -> dict:
    rec = dict(row)
    id_ = rec["submission_id"]
    errors: list[str] = []
    submitted = _iso_date(rec["submitted_on"])
    if submitted is None:
        errors.append("INVALID_SUBMISSION_DATE")
    built = rec["year_built"]
    if built is None:
        errors.append("AIRCRAFT_YEAR_MISSING")
    elif submitted is not None and built > submitted.year:
        errors.append("AIRCRAFT_BUILT_AFTER_SUBMISSION")
    if rec["pilot_id"] is None or rec["total_flight_hours"] is None or rec["make_model_hours"] is None:
        errors.append("PILOT_EVIDENCE_MISSING")
    elif rec["make_model_hours"] > rec["total_flight_hours"]:
        errors.append("PILOT_HOURS_CONTRADICTORY")
    if rec["recurrent_training_verified"] is None:
        errors.append("RECURRENT_TRAINING_MISSING")
    if rec["losses_last_five_years"] is None:
        errors.append("LOSS_HISTORY_MISSING")
    if rec["annual_flight_hours"] is None:
        errors.append("ANNUAL_FLIGHT_HOURS_MISSING")
    if rec["requested_hull_value_usd"] is None:
        errors.append("HULL_VALUE_MISSING_FOR_SEVERITY")
    if rec["mro_severity_days"] is None or rec["mro_cost_pressure_index"] is None:
        errors.append("MRO_COVERAGE_MISSING")
    for timestamp in ("oldest_observation", "latest_observation"):
        value = rec[timestamp]
        observed = _iso_date(value)
        if value is not None and observed is None:
            errors.append("MRO_OBSERVATION_DATE_INVALID")
        elif observed is not None and submitted is not None:
            age = (submitted - observed).days
            if age < 0:
                errors.append("MRO_OBSERVATION_FROM_FUTURE")
            elif age > 30:
                errors.append("MRO_OBSERVATION_STALE")
    if not source_integrity_ok:
        errors.append("SOURCE_INTEGRITY_BLOCKED")
    if not policy_ok:
        errors.append("MODEL_POLICY_BLOCKED")
    if rec["insufficient_evidence"] and (rec["risk_points"] is not None or rec["triage_recommendation"] != "Refer"):
        errors.append("EVIDENCE_GATE_INCONSISTENT")
    # An apparently decisive classification with any missing or conflicting
    # evidence is a release-blocking logic bug, rather than an underwriting result.
    if errors and rec["triage_recommendation"] in ("Quote", "Decline"):
        errors.append("DECISIVE_LABEL_WITH_EVIDENCE_GAP")
    blockers = {"SOURCE_INTEGRITY_BLOCKED", "MODEL_POLICY_BLOCKED",
                "AIRCRAFT_BUILT_AFTER_SUBMISSION", "PILOT_HOURS_CONTRADICTORY",
                "EVIDENCE_GATE_INCONSISTENT", "DECISIVE_LABEL_WITH_EVIDENCE_GAP",
                "INVALID_SUBMISSION_DATE", "MRO_OBSERVATION_DATE_INVALID"}
    return {"submission_id": id_, "research_label": rec["triage_recommendation"],
            "risk_points": rec["risk_points"],
            "quality_status": ("BLOCKED" if any(e in blockers for e in errors) else
                               "REFER_FOR_REVIEW" if errors else "INPUTS_PRESENT_SYNTHETIC"),
            "issue_codes": sorted(set(errors)),
            "underwriter_authority": "HUMAN_REVIEW_REQUIRED"}


def audit_database(db: Path) -> dict:
    """Reconcile all stored dataset snapshots to import fingerprints in read-only mode."""
    if not db.is_file():
        raise FileNotFoundError(db)
    with sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True) as con:
        con.row_factory = sqlite3.Row
        if con.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("SQLite integrity check failed")
        if con.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("Database contains broken foreign-key references")
        source = _source_checks(con)
        dimensions = _dimension_checks(con)
        policy = _policy_check(con)
        dimension_ok = all(x["status"] == "FINGERPRINT_MATCH_ONLY" for x in dimensions)
        source_ok = (all(x["status"] == "FINGERPRINT_MATCH_ONLY" for x in source)
                     and dimension_ok)
        policy_ok = policy["status"] == "EXPECTED_SYNTHETIC_POLICY"
        cases = [_submission_check(row, source_integrity_ok=source_ok, policy_ok=policy_ok)
                 for row in con.execute("SELECT * FROM v_submission_triage ORDER BY submission_id")]
    if not cases:
        raise ValueError("No submissions to validate")
    blockers = [s for s in cases if s["quality_status"] == "BLOCKED"]
    return {
        "schema": SCHEMA,
        "synthetic": True,
        "data_mode": "SYNTHETIC_ONLY",
        "model_version": underwriting_pipeline.VERSION,
        "database_sha256": hashlib.sha256(db.read_bytes()).hexdigest(),
        "source_checks": source,
        "dimension_checks": dimensions,
        "policy_check": policy,
        "submissions": cases,
        "summary": {
            "total_submissions": len(cases),
            "inputs_present": sum(c["quality_status"] == "INPUTS_PRESENT_SYNTHETIC" for c in cases),
            "referred_for_missing_evidence": sum(c["quality_status"] == "REFER_FOR_REVIEW" for c in cases),
            "blocked_submissions": len(blockers),
            "source_fingerprints_matched": sum(s["status"] == "FINGERPRINT_MATCH_ONLY" for s in source),
            "source_fingerprints_expected": len(SOURCE_TABLES),
            "dimension_fingerprints_matched": sum(s["status"] == "FINGERPRINT_MATCH_ONLY" for s in dimensions),
            "dimension_fingerprints_expected": len(DIMENSION_TABLES),
        },
        "quality_gate": "BLOCKED" if blockers or not source_ok or not policy_ok else "INTERNAL_DEMO_ONLY",
        "predicted_loss_accuracy": "NOT_CALIBRATED",
        "external_release_authorized": False,
    }


def require_pass(audit: dict) -> None:
    if audit["quality_gate"] != "INTERNAL_DEMO_ONLY":
        raise ValueError("Underwriting source or model integrity blocked; see the quality audit")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)
    try:
        if args.out.suffix.lower() != ".json" or args.out.exists() or args.out.resolve() == args.db.resolve():
            raise ValueError("Quality audit requires a fresh JSON output path")
        result = audit_database(args.db)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("x", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print(json.dumps({"output": str(args.out), "gate": result["quality_gate"],
                          "total_submissions": result["summary"]["total_submissions"]}))
        return 0 if result["quality_gate"] == "INTERNAL_DEMO_ONLY" else 1
    except (OSError, ValueError, sqlite3.Error, TypeError, KeyError) as exc:
        print(f"Quality audit refused: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
