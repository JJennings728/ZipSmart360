"""Replaceable, offline-only adapters for the synthetic AeroCIE prime SCRM pilot.

No network access, external LLM calls, non-synthetic data or claims of MOSA
conformance. Accepted inputs are versioned JSON or an integrity-pinned CSV bundle.

Usage (from aviation-ai-workflow):
  python -m src.aerocie.prime_adapters --adapter json --source sample-data/prime_scrm_synthetic.json
  python -m src.aerocie.prime_adapters --adapter csv --source PATH_TO_SYNTHETIC_BUNDLE
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import re
from typing import Any

from .prime_pilot import SCHEMA, evaluate, persist_new

BUNDLE_SCHEMA = "SRP-SCRM-CSV-BUNDLE-v1"
MAX_JSON_BYTES = 1_000_000
MAX_CSV_BYTES = 256_000
CSV_HEADERS = {
    "evidence.csv": ("evidence_id", "text", "sha256", "synthetic"),
    "suppliers.csv": ("supplier_id", "name"),
    "components.csv": (
        "component_id", "supplier_id", "evidence_id",
        "baseline_lead_days", "scenario_lead_days",
        "critical_path_assumed", "single_source_assumed",
    ),
}
SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key rejected")
        result[key] = value
    return result


def _no_nonfinite(_: str) -> None:
    raise ValueError("Non-finite JSON number rejected")


def _read_regular(path: Path, limit: int) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ValueError("Source must be an existing regular, non-symlink file")
    if path.stat().st_size > limit:
        raise ValueError("Source exceeds configured size limit")
    data = path.read_bytes()
    if len(data) > limit:
        raise ValueError("Source exceeds configured size limit")
    return data


def _decode_json(raw: bytes) -> dict[str, Any]:
    obj = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object,
                     parse_constant=_no_nonfinite)
    if not isinstance(obj, dict):
        raise ValueError("JSON source must be an object")
    return obj


def _flag(value: str, field: str) -> bool:
    if value not in ("true", "false"):
        raise ValueError(f"{field} must be true or false")
    return value == "true"


def _nonnegative_whole(value: str, field: str) -> int:
    if not isinstance(value, str) or re.fullmatch(r"[0-9]{1,4}", value) is None:
        raise ValueError(f"{field} must be a nonnegative whole number")
    return int(value)


def load_json(path: Path) -> dict[str, Any]:
    """Load a bounded local JSON file. Downstream evaluation enforces policy."""
    return _decode_json(_read_regular(path, MAX_JSON_BYTES))


def _rows(raw: bytes, name: str) -> list[dict[str, str]]:
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8"), newline=""), strict=True)
    if tuple(reader.fieldnames or ()) != CSV_HEADERS[name]:
        raise ValueError(f"Unexpected {name} column headers")
    result = []
    for record in reader:
        if set(record) != set(CSV_HEADERS[name]):
            raise ValueError(f"Unexpected or missing columns in {name}")
        if any(value is None for value in record.values()):
            raise ValueError(f"Incomplete CSV row in {name}")
        result.append(record)
        if len(result) > 1000:
            raise ValueError(f"Too many rows in {name}")
    if not result:
        raise ValueError(f"Empty {name}")
    return result


def load_csv_bundle(root: Path) -> dict[str, Any]:
    """Read exactly three fixed CSV files with manifest-pinned byte fingerprints.

    File names are fixed by this module, not influenced by user-supplied manifest
    paths. This is an offline integration proof, not external source authentication.
    """
    if root.is_symlink() or not root.is_dir():
        raise ValueError("CSV source must be a non-symlink directory")
    manifest = _decode_json(_read_regular(root / "manifest.json", MAX_JSON_BYTES))
    if manifest.get("bundle_schema") != BUNDLE_SCHEMA:
        raise ValueError("Unsupported CSV bundle schema")
    expected = manifest.get("files")
    if not isinstance(expected, dict) or set(expected) != set(CSV_HEADERS):
        raise ValueError("Manifest file allowlist mismatch")
    rows: dict[str, list[dict[str, str]]] = {}
    for name in CSV_HEADERS:
        pin = expected[name]
        if not isinstance(pin, str) or SHA256.fullmatch(pin) is None:
            raise ValueError(f"Invalid SHA-256 pin for {name}")
        raw = _read_regular(root / name, MAX_CSV_BYTES)
        if hashlib.sha256(raw).hexdigest() != pin:
            raise ValueError(f"Integrity mismatch for {name}")
        rows[name] = _rows(raw, name)
    evidence = [
        {
            "evidence_id": row["evidence_id"],
            "text": row["text"],
            "sha256": row["sha256"],
            "synthetic": _flag(row["synthetic"], "synthetic"),
        }
        for row in rows["evidence.csv"]
    ]
    components = [
        {
            "component_id": row["component_id"],
            "supplier_id": row["supplier_id"],
            "evidence_id": row["evidence_id"],
            "baseline_lead_days": _nonnegative_whole(
                row["baseline_lead_days"], "baseline_lead_days"),
            "scenario_lead_days": _nonnegative_whole(
                row["scenario_lead_days"], "scenario_lead_days"),
            "critical_path_assumed": _flag(
                row["critical_path_assumed"], "critical_path_assumed"),
            "single_source_assumed": _flag(
                row["single_source_assumed"], "single_source_assumed"),
        }
        for row in rows["components.csv"]
    ]
    return {
        "schema": manifest.get("schema"),
        "data_classification": manifest.get("data_classification"),
        "external_release_authorized": manifest.get("external_release_authorized"),
        "program": manifest.get("program"),
        "evidence": evidence,
        "suppliers": rows["suppliers.csv"],
        "components": components,
    }


def evaluate_source(adapter: str, source: Path) -> dict[str, Any]:
    """The risk model is unchanged when the input adapter changes."""
    if adapter == "json":
        payload = load_json(source)
    elif adapter == "csv":
        payload = load_csv_bundle(source)
    else:
        raise ValueError("Adapter must be json or csv")
    return evaluate(payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline AeroCIE source-adapter validation")
    parser.add_argument("--adapter", required=True, choices=("json", "csv"))
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--db", type=Path)
    args = parser.parse_args(argv)
    if args.out is not None and args.out.exists():
        parser.error("Refusing to overwrite report output")
    if args.db is not None and args.db.exists():
        parser.error("Refusing to overwrite SQLite output")
    if args.out is not None and args.db is not None and args.out.resolve() == args.db.resolve():
        parser.error("Report and SQLite output paths must differ")
    try:
        report = evaluate_source(args.adapter, args.source)
        if args.db:
            persist_new(args.db, report)
        rendered = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            with args.out.open("x", encoding="utf-8") as file:
                file.write(rendered)
        else:
            print(rendered, end="")
        return 0
    except (OSError, ValueError, TypeError, csv.Error) as exc:
        parser.exit(2, f"Source adapter error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
