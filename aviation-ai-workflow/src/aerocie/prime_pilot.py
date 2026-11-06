"""Offline synthetic-only aerospace supplier-dependency screening pilot.

No network, AI services, customer records, or regulatory/conformity opinions.
Input and output use documented versioned JSON for replaceable integration.
Run from aviation-ai-workflow: python -m src.aerocie.prime_pilot --input sample-data/prime_scrm_synthetic.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
from contextlib import closing

SCHEMA = "SRP-PRIME-SCRM-v1"
RELEASE_MODE = "INTERNAL_SYNTHETIC_ONLY"


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def _records(payload: dict, name: str) -> list[dict]:
    value = payload.get(name)
    if not isinstance(value, list) or not value:
        raise ValueError(f"{name} must be a nonempty list")
    if not all(isinstance(item, dict) for item in value):
        raise ValueError(f"{name} rows must be objects")
    return value


def _index(rows: list[dict], field: str, label: str) -> dict[str, dict]:
    result = {}
    for item in rows:
        key = item.get(field)
        if not isinstance(key, str) or not key or len(key) > 80 or key in result:
            raise ValueError(f"Invalid or duplicate {label} ID")
        result[key] = item
    return result


def _days(value: object, field: str) -> int:
    if type(value) is not int or value < 0 or value > 3650:
        raise ValueError(f"{field} must be a whole number from 0 to 3650")
    return value


def evaluate(payload: dict) -> dict:
    """Fail closed on provenance, references, and synthetic-only input scope."""
    if not isinstance(payload, dict):
        raise ValueError("Expected a JSON object")
    if payload.get("schema") != SCHEMA:
        raise ValueError("Unsupported input schema")
    if payload.get("data_classification") != "PUBLIC_SYNTHETIC_ONLY":
        raise ValueError("Only explicitly synthetic inputs are allowed")
    if payload.get("external_release_authorized") is not False:
        raise ValueError("External release must be explicitly disabled")
    program = payload.get("program")
    if not isinstance(program, str) or not (1 <= len(program) <= 120):
        raise ValueError("Missing or invalid program label")

    sources = _index(_records(payload, "evidence"), "evidence_id", "evidence")
    suppliers = _index(_records(payload, "suppliers"), "supplier_id", "supplier")
    components = _index(_records(payload, "components"), "component_id", "component")
    for sid, row in sources.items():
        excerpt = row.get("text")
        if not isinstance(excerpt, str) or not excerpt.strip() or len(excerpt) > 4000:
            raise ValueError(f"Missing or invalid evidence text: {sid}")
        expected = hashlib.sha256(excerpt.encode("utf-8")).hexdigest()
        if row.get("sha256") != expected:
            raise ValueError(f"Evidence fingerprint mismatch: {sid}")
        if row.get("synthetic") is not True:
            raise ValueError(f"Evidence is not marked synthetic: {sid}")
    for sid, row in suppliers.items():
        if not isinstance(row.get("name"), str) or not row["name"].strip():
            raise ValueError(f"Missing supplier name: {sid}")

    items = []
    for cid, row in sorted(components.items()):
        supplier_id = row.get("supplier_id")
        evidence_id = row.get("evidence_id")
        if supplier_id not in suppliers or evidence_id not in sources:
            raise ValueError(f"Unresolved supplier or evidence reference: {cid}")
        baseline = _days(row.get("baseline_lead_days"), "baseline_lead_days")
        scenario = _days(row.get("scenario_lead_days"), "scenario_lead_days")
        critical = row.get("critical_path_assumed")
        single = row.get("single_source_assumed")
        if type(critical) is not bool or type(single) is not bool:
            raise ValueError(f"Assumption flags must be booleans: {cid}")
        increase = max(0, scenario - baseline)
        items.append({
            "component_id": cid,
            "supplier_id": supplier_id,
            "supplier_name": suppliers[supplier_id]["name"],
            "evidence_id": evidence_id,
            "baseline_lead_days": baseline,
            "scenario_lead_days": scenario,
            "lead_time_increase_days": increase,
            "critical_path_assumed": critical,
            "single_source_assumed": single,
            "review_flag": increase > 0 or single,
            "interpretation": "ASSUMPTION_BASED_SCREENING_NOT_FORECAST",
        })
    critical_increases = [x["lead_time_increase_days"] for x in items
                          if x["critical_path_assumed"]]
    summary = {
        "components_evaluated": len(items),
        "supplier_count": len(suppliers),
        "review_flag_count": sum(x["review_flag"] for x in items),
        "single_source_assumptions": sum(x["single_source_assumed"] for x in items),
        "largest_assumed_critical_component_increase_days": max(critical_increases, default=None),
        "schedule_forecast": "NOT_AVAILABLE_NO_VALIDATED_DEPENDENCY_NETWORK",
    }
    result = {
        "schema": SCHEMA,
        "program": program,
        "status": RELEASE_MODE,
        "external_release_authorized": False,
        "input_sha256": digest(payload),
        "summary": summary,
        "components": items,
        "limitations": [
            "Synthetic evidence only; fingerprints establish integrity, not source authority.",
            "Component lead-time changes do not establish actual project schedule delays.",
            "Critical path and single-source status are unverified scenario assumptions.",
            "No actual supplier mapping, purchase orders, forecasts, CUI, or classified data.",
            "No MOSA conformance, CMMC assessment, cybersecurity authorization, or contract award.",
        ],
    }
    result["report_sha256"] = digest(result)
    return result


def persist_new(db: Path, report: dict) -> None:
    """Write one immutable local evidence-screening report; never replace existing DB."""
    if db.exists():
        raise FileExistsError(f"Refusing to overwrite: {db}")
    db.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(db)) as con:
        with con:
            con.execute("PRAGMA foreign_keys=ON")
            con.execute("CREATE TABLE reports (report_sha256 TEXT PRIMARY KEY, schema_version TEXT NOT NULL, input_sha256 TEXT NOT NULL, report_json TEXT NOT NULL)")
            con.execute("CREATE TABLE component_screen (report_sha256 TEXT NOT NULL REFERENCES reports(report_sha256), component_id TEXT NOT NULL, supplier_id TEXT NOT NULL, evidence_id TEXT NOT NULL, lead_time_increase_days INTEGER NOT NULL, review_flag INTEGER NOT NULL, PRIMARY KEY(report_sha256, component_id))")
            con.execute("INSERT INTO reports VALUES (?,?,?,?)", (report["report_sha256"], report["schema"], report["input_sha256"], json.dumps(report, sort_keys=True)))
            con.executemany("INSERT INTO component_screen VALUES (?,?,?,?,?,?)", [
                (report["report_sha256"], x["component_id"], x["supplier_id"], x["evidence_id"], x["lead_time_increase_days"], int(x["review_flag"]))
                for x in report["components"]
            ])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline synthetic aerospace supplier dependency screening")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--db", type=Path)
    args = parser.parse_args(argv)
    if args.out and args.out.exists():
        parser.error("Refusing to overwrite existing JSON output")
    if args.db and args.db.exists():
        parser.error("Refusing to overwrite existing SQLite database")
    try:
        raw = json.loads(args.input.read_text(encoding="utf-8"))
        report = evaluate(raw)
        if args.db:
            persist_new(args.db, report)
        encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            with args.out.open("x", encoding="utf-8") as output_file:
                output_file.write(encoded)
        else:
            print(encoded, end="")
        return 0
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        parser.exit(2, f"Input or output error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
