"""AeroCIE-014: local self-attested research-review journal.

Append-only application-level SQLite audit, chained local SHA-256 evidence,
not an authenticated signature, FAA delegation, or regulatory approval.
"""
from __future__ import annotations
import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
from .audit_packet import CHECKS, verify_packet_hash

STATUSES = ("CHECKED_RESEARCH_ONLY", "FOLLOW_UP_REQUIRED")
ATTESTATION = (
    "I personally performed the described internal research step. "
    "This record does not certify FAA applicability, compliance, "
    "source completeness or approval for external release."
)
SCHEMA = "AEROCIE-014-REVIEW-JOURNAL-v1"


def _digest(data: dict) -> str:
    data_bytes = json.dumps(
        data, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(data_bytes).hexdigest()


def _packet(path: Path) -> dict:
    if not path.is_file():
        raise ValueError("Unsigned AeroCIE-013 packet file is missing")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not verify_packet_hash(data):
        raise ValueError("Packet integrity checksum failed")
    if (data.get("packet_schema") != "AEROCIE-013-UNSIGNED-RESEARCH-DRAFT-v1"
            or data.get("external_release_authorized") is not False
            or data.get("human_review_complete") is not False
            or data.get("compliance_status") != "NOT_DETERMINED"
            or data.get("review_disposition") != "HOLD_FOR_HUMAN_REVIEW"):
        raise ValueError("This tool requires an unchanged, unsigned research packet")
    declared = [r.get("check_id") for r in data.get("human_review_checklist", [])]
    if declared != [name for name, _ in CHECKS]:
        raise ValueError("Packet review checklist is not the expected version")
    return data


def _validate_journal_path(journal: Path, packet_path: Path) -> None:
    if journal.resolve() == packet_path.resolve():
        raise ValueError("The review journal must not overwrite the packet")
    if journal.suffix.lower() != ".sqlite3":
        raise ValueError("Review journal path must end in .sqlite3")


def _open_existing(journal: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(journal.resolve().as_uri() + "?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _check_schema(conn: sqlite3.Connection) -> None:
    names = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%'")}
    if names and names != {"review_meta", "review_events"}:
        raise ValueError("Refusing to reuse a non-review database")


def _history(conn: sqlite3.Connection, packet_hash: str) -> list[dict]:
    meta = conn.execute(
        "SELECT packet_sha256, schema_version FROM review_meta WHERE id=1"
    ).fetchone()
    if meta is None or meta[0] != packet_hash or meta[1] != SCHEMA:
        raise ValueError("Ledger belongs to another packet or has invalid metadata")
    history = []
    previous = "0" * 64
    for seq, payload, stored in conn.execute(
        "SELECT seq, event_json, event_sha256 FROM review_events ORDER BY seq"):
        data = json.loads(payload)
        if (not isinstance(data, dict)
                or seq != len(history) + 1
                or data.get("sequence") != seq
                or data.get("packet_sha256") != packet_hash
                or data.get("previous_event_sha256") != previous
                or stored != _digest(data)):
            raise ValueError("Review journal chain mismatch: review required")
        history.append(data)
        previous = stored
    return history


def _initialize(conn: sqlite3.Connection, packet_hash: str) -> None:
    _check_schema(conn)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS review_meta("
        "id INTEGER PRIMARY KEY CHECK(id=1),"
        "packet_sha256 TEXT NOT NULL,"
        "schema_version TEXT NOT NULL)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS review_events("
        "seq INTEGER PRIMARY KEY,"
        "event_json TEXT NOT NULL,"
        "event_sha256 TEXT NOT NULL)"
    )
    conn.execute(
        "CREATE TRIGGER IF NOT EXISTS review_events_no_update "
        "BEFORE UPDATE ON review_events BEGIN "
        "SELECT RAISE(ABORT, 'review history is append-only'); END"
    )
    conn.execute(
        "CREATE TRIGGER IF NOT EXISTS review_events_no_delete "
        "BEFORE DELETE ON review_events BEGIN "
        "SELECT RAISE(ABORT, 'review history is append-only'); END"
    )
    if conn.execute("SELECT COUNT(*) FROM review_meta").fetchone()[0] == 0:
        conn.execute(
            "INSERT INTO review_meta(id, packet_sha256, schema_version)"
            " VALUES (1,?,?)", (packet_hash, SCHEMA)
        )
    _history(conn, packet_hash)


def _field(value: str, title: str, lower: int, upper: int) -> str:
    if not isinstance(value, str):
        raise ValueError(title + " must be text")
    cleaned = value.strip()
    if (not lower <= len(cleaned) <= upper
            or any(ord(c) < 32 and c not in "\n\t" for c in cleaned)):
        raise ValueError(title + " must have valid length and characters")
    return cleaned


def record_check(packet_path: Path, journal: Path, *,
                 check_id: str, status: str, reviewer: str, reviewer_role: str,
                 notes: str, citation: str = "", attest: bool = False) -> dict:
    packet = _packet(packet_path)
    _validate_journal_path(journal, packet_path)
    if check_id not in {name for name, _ in CHECKS}:
        raise ValueError("Unknown checklist item")
    if status not in STATUSES:
        raise ValueError("Only research-checked or follow-up-required states allowed")
    if attest is not True:
        raise ValueError("Explicit personal research-step attestation is required")
    reviewer = _field(reviewer, "Reviewer", 2, 120)
    reviewer_role = _field(reviewer_role, "Reviewer role", 2, 160)
    notes = _field(notes, "Specific checks performed or outstanding questions", 30, 4000)
    citation = _field(citation, "Source citation", 0, 1500)
    if status == "CHECKED_RESEARCH_ONLY" and len(citation) < 10:
        raise ValueError("Research-checked entry requires a specific citation")
    journal.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(journal, timeout=20)) as conn:
        conn.execute("BEGIN IMMEDIATE")
        _initialize(conn, packet["audit_sha256"])
        history = _history(conn, packet["audit_sha256"])
        prior = _digest(history[-1]) if history else "0" * 64
        event = {
            "schema": SCHEMA,
            "sequence": len(history) + 1,
            "packet_sha256": packet["audit_sha256"],
            "recorded_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "check_id": check_id,
            "status": status,
            "reviewer": reviewer,
            "reviewer_role": reviewer_role,
            "notes": notes,
            "citation": citation,
            "attestation": ATTESTATION,
            "identity_authenticated": False,
            "faa_approval": False,
            "applicability_determined": False,
            "external_release_authorized": False,
            "previous_event_sha256": prior,
        }
        digest = _digest(event)
        conn.execute(
            "INSERT INTO review_events(seq,event_json,event_sha256)"
            " VALUES (?,?,?)",
            (len(history) + 1, json.dumps(event, ensure_ascii=False), digest)
        )
        conn.commit()
    return {
        "recorded_sequence": event["sequence"],
        "check_id": check_id,
        "status": status,
        "local_event_sha256": digest,
        "human_review_complete": False,
        "external_release_authorized": False,
    }


def summary(packet_path: Path, journal: Path) -> dict:
    packet = _packet(packet_path)
    _validate_journal_path(journal, packet_path)
    if journal.is_file():
        with closing(_open_existing(journal)) as conn:
            _check_schema(conn)
            history = _history(conn, packet["audit_sha256"])
    else:
        history = []
    latest = {key: "PENDING_HUMAN_REVIEW" for key, _ in CHECKS}
    for event in history:
        if event["check_id"] not in latest or event["status"] not in STATUSES:
            raise ValueError("Invalid review event state")
        latest[event["check_id"]] = event["status"]
    return {
        "packet_sha256": packet["audit_sha256"],
        "journal_event_count": len(history),
        "latest_checklist_states": latest,
        "events": history,
        "review_disposition": "HOLD_FOR_HUMAN_REVIEW",
        "human_review_complete": False,
        "compliance_status": "NOT_DETERMINED",
        "applicability_status": "NOT_DETERMINED",
        "external_release_authorized": False,
        "limitations": (
            "Self-attested local research step records only; the recorded identity "
            "and source citation are not independently authenticated. Even eight "
            "CHECKED_RESEARCH_ONLY entries are not an FAA approval, legal "
            "applicability conclusion or authorization for customer release."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="AeroCIE-014 offline self-attested research-review journal"
    )
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--journal", type=Path, required=True)
    options = parser.add_subparsers(dest="command", required=True)
    record = options.add_parser("record-check")
    record.add_argument("--check-id", required=True)
    record.add_argument("--status", choices=STATUSES, required=True)
    record.add_argument("--reviewer", required=True)
    record.add_argument("--reviewer-role", required=True)
    record.add_argument("--notes", required=True)
    record.add_argument("--citation", default="")
    record.add_argument("--attest", action="store_true")
    options.add_parser("status")
    args = parser.parse_args(argv)
    try:
        if args.command == "record-check":
            result = record_check(
                args.packet, args.journal, check_id=args.check_id,
                status=args.status, reviewer=args.reviewer,
                reviewer_role=args.reviewer_role, notes=args.notes,
                citation=args.citation, attest=args.attest
            )
        else:
            result = summary(args.packet, args.journal)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, sqlite3.Error, KeyError, TypeError,
            json.JSONDecodeError) as exc:
        print("AeroCIE-014 review journal error:", exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
