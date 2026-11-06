"""AeroCIE-033 | controlled offline export of synthetic-only review demonstration.

Makes a watermarked ZIP for internal technical evaluation. This is NOT a
customer export, source authentication, security assessment or release approval.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import zipfile

from .prime_pilot import digest
from .review_decision_ledger import _key_from_env, _packet_checked, verify

EXPORT_SCHEMA = "SRP-INTERNAL-SYNTHETIC-EXPORT-v1"
README = """STRATEGICRISK PARTNERS | AEROCIE INTERNAL SYNTHETIC DEMONSTRATION

NOT FOR CUSTOMER DELIVERY. NOT CLEARED FOR PRODUCTION. NOT APPROVED FOR CUI,
FCI, EXPORT-CONTROLLED INFORMATION, CLASSIFIED DATA, OR LIVE SUPPLIER RECORDS.

All input records are fictional and self-declared synthetic.
The captured reviewer identifiers are self-declared, NOT identity-authenticated.
An HMAC validates key possession, NOT a person's identity or legal signature.
Fingerprints validate local integrity only, NOT the supplier/source's authenticity.
All research acknowledgements are limited to a synthetic internal demonstration.
This package does not authorize any external release, contractual compliance
claim, supplier approval, program schedule forecast or insurance decision.
No CMMC certification or MOSA conformance is established.
"""


def _bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False,
                       allow_nan=False) + "\n").encode("utf-8")


def _read_packet(db: Path) -> dict:
    if db.is_symlink() or not db.is_file():
        raise FileNotFoundError("Journal not found or symlink disallowed")
    with closing(sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True)) as con:
        row = con.execute(
            "SELECT packet_json,packet_sha256 FROM journal_meta WHERE singleton=1"
        ).fetchone()
        if row is None:
            raise ValueError("Missing journal packet")
        packet = json.loads(row[0])
        _packet_checked(packet)
        if row[1] != packet["packet_sha256"]:
            raise ValueError("Packet digest mismatch")
        return packet


def _latest_decisions(packet: dict, verified: dict) -> list[dict]:
    """Require every flagged synthetic finding to be most recently acknowledged."""
    latest: dict[str, dict] = {}
    for item in verified["events"]:
        event = item["event"]
        latest[event["component_id"]] = event
    result = []
    for review in packet["open_review_items"]:
        cid = review["component_id"]
        event = latest.get(cid)
        if event is None:
            raise ValueError(f"Research finding has no recorded decision: {cid}")
        if event["decision"] != "RESEARCH_ACKNOWLEDGED":
            raise ValueError(f"Research finding is not acknowledged: {cid}")
        result.append({
            "component_id": cid,
            "evidence_id": review["evidence_id"],
            "evidence_sha256": review["evidence_sha256"],
            "reviewer_id_self_declared": event["reviewer_id"],
            "disposition": "RESEARCH_ACKNOWLEDGED",
            "event_seq": event["seq"],
            "recorded_utc_self_reported": event["recorded_utc"],
        })
    if not result:
        raise ValueError("No reviewable findings; export requires a reviewed demonstration")
    return result


def create_internal_export(db: Path, output: Path, *, key: bytes,
                           expected_head: str) -> dict:
    """Write a NEW deterministic ZIP only after synthetic / HMAC / anchor gates."""
    if not isinstance(expected_head, str) or len(expected_head) != 64:
        raise ValueError("Externally retained 64-character head SHA-256 is required")
    # Force verification against an independent caller-supplied journal anchor;
    # without it a truncated tail can look valid.
    verified = verify(db, key, expected_head)
    if not verified["externally_anchored"] or verified["event_count"] == 0:
        raise ValueError("At least one anchored review event required")
    packet = _read_packet(db)
    if packet["packet_sha256"] != verified["packet_sha256"]:
        raise ValueError("Packet and journal provenance mismatch")
    reviews = _latest_decisions(packet, verified)
    if output.exists() or output.is_symlink():
        raise FileExistsError("Refusing to replace an existing exported package")
    if output.suffix.lower() != ".zip":
        raise ValueError("Internal package output must use .zip")
    artifact = {
        "schema": EXPORT_SCHEMA,
        "release_authorized": False,
        "classification": "PUBLIC_SYNTHETIC_ONLY",
        "watermark": "INTERNAL SYNTHETIC RESEARCH ONLY — NOT FOR CUSTOMER DELIVERY",
        "packet_sha256": verified["packet_sha256"],
        "head_sha256": verified["head_sha256"],
        "head_anchored_to_user_supplied_value": True,
        "review_event_count": verified["event_count"],
        "research_acknowledgements": reviews,
        "summary": packet["model_summary"],
        "source_counts": packet["source_counts"],
        "data_quality_findings": packet["data_quality_findings"],
        "source_record_sha256": packet["source_record_sha256"],
        "limitations": packet["limitations"] + [
            "HMAC does not verify the real identity or legal authority of a reviewer.",
            "The packet is an internal synthetic sample and carries no external release permission.",
        ],
    }
    artifact["artifact_sha256"] = digest(artifact)
    reports = {
        "READ_ME_FIRST.txt": README.encode("utf-8"),
        "internal_research_report.json": _bytes(artifact),
    }
    manifest = {
        "schema": EXPORT_SCHEMA,
        "release_authorized": False,
        "head_sha256": verified["head_sha256"],
        "files_sha256": {
            name: hashlib.sha256(data).hexdigest()
            for name, data in sorted(reports.items())
        },
    }
    manifest["manifest_sha256"] = digest(manifest)
    reports["manifest.json"] = _bytes(manifest)
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with output.open("xb") as target:
            with zipfile.ZipFile(target, "w") as archive:
                for name, data in sorted(reports.items()):
                    item = zipfile.ZipInfo(filename=name, date_time=(1980, 1, 1, 0, 0, 0))
                    item.compress_type = zipfile.ZIP_DEFLATED
                    item.external_attr = 0o600 << 16
                    archive.writestr(item, data)
    except BaseException:
        if output.is_file():
            output.unlink()
        raise
    return {
        "schema": EXPORT_SCHEMA,
        "status": "INTERNAL_SYNTHETIC_ONLY",
        "external_release_authorized": False,
        "package_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "journal_head_sha256": verified["head_sha256"],
        "acknowledged_components": len(reviews),
        "output": str(output),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export watermarked internal AeroCIE demo")
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--expected-head", required=True)
    args = parser.parse_args(argv)
    try:
        result = create_internal_export(
            args.db, args.out, key=_key_from_env(), expected_head=args.expected_head
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, sqlite3.Error, zipfile.BadZipFile) as exc:
        parser.exit(2, f"Internal demo export rejected: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
