"""AeroCIE-032: offline synthetic research review ledger with integrity checks.

NOT an identity provider, legal electronic signature, digital certificate,
immutable store, CUI system, or authority to release/approve real-world work.
HMAC is symmetric-key evidence of possession of a local test key, not proof
that the self-declared reviewer is a particular human.
"""
from __future__ import annotations

import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import sqlite3
from typing import Any

from .prime_pilot import digest
from .prime_reconciliation import PACKET_SCHEMA

JOURNAL_SCHEMA = "SRP-REVIEW-JOURNAL-v1"
DECISIONS = ("RESEARCH_ACKNOWLEDGED", "MORE_EVIDENCE_REQUIRED", "REJECT_RESEARCH_FINDING")
ACTOR = re.compile(r"[A-Z][A-Z0-9_-]{2,31}\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
ENV_NAME = "SRP_REVIEW_HMAC_KEY_HEX"
GENESIS = "0" * 64


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False)


def _key_from_env() -> bytes:
    raw = os.environ.get(ENV_NAME, "")
    if not re.fullmatch(r"[0-9a-fA-F]{64,128}", raw):
        raise ValueError(f"Set {ENV_NAME} to a locally generated 32–64 byte hex test key")
    return bytes.fromhex(raw)


def _packet_checked(packet: dict) -> dict:
    if not isinstance(packet, dict) or packet.get("schema") != PACKET_SCHEMA:
        raise ValueError("Unrecognized review packet schema")
    if (packet.get("classification") != "PUBLIC_SYNTHETIC_ONLY"
            or packet.get("release_authorized") is not False
            or packet.get("decision_status") != "HUMAN_REVIEW_REQUIRED"
            or packet.get("reviewer_disposition") != "NOT_RECORDED"):
        raise ValueError("Only unreleased, synthetic, unreviewed research packets permitted")
    recorded = packet.get("packet_sha256")
    if not isinstance(recorded, str) or HEX64.fullmatch(recorded) is None:
        raise ValueError("Packet fingerprint missing")
    if not hmac.compare_digest(recorded, digest({k: v for k, v in packet.items()
                                                if k != "packet_sha256"})):
        raise ValueError("Packet fingerprint invalid")
    queue = packet.get("open_review_items")
    if not isinstance(queue, list) or any(not isinstance(row, dict) for row in queue):
        raise ValueError("Review queue is invalid")
    by_id = {}
    for row in queue:
        key = row.get("component_id")
        if (not isinstance(key, str) or not key or key in by_id
                or row.get("human_disposition") != "OPEN_NOT_REVIEWED"
                or not isinstance(row.get("evidence_id"), str)
                or not isinstance(row.get("evidence_sha256"), str)
                or HEX64.fullmatch(row["evidence_sha256"]) is None):
            raise ValueError("Invalid or duplicate synthetic review target")
        by_id[key] = row
    return by_id


def _signature(key: bytes, event_digest: str) -> str:
    return hmac.new(key, event_digest.encode("ascii"), hashlib.sha256).hexdigest()


def initialize(db: Path, packet: dict) -> str:
    """Create a fresh, local journal without replacing an existing file."""
    _packet_checked(packet)
    if db.exists() or db.is_symlink():
        raise FileExistsError("Refusing to replace an existing journal")
    db.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(db, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(descriptor)
    with closing(sqlite3.connect(db)) as con:
        con.execute("PRAGMA foreign_keys=ON")
        with con:
            con.execute(
                "CREATE TABLE journal_meta (singleton INTEGER PRIMARY KEY CHECK(singleton=1), "
                "schema_version TEXT NOT NULL, packet_sha256 TEXT NOT NULL, "
                "packet_json TEXT NOT NULL)"
            )
            con.execute(
                "CREATE TABLE review_events (seq INTEGER PRIMARY KEY, "
                "event_json TEXT NOT NULL, event_sha256 TEXT NOT NULL, "
                "hmac_sha256 TEXT NOT NULL)"
            )
            con.execute("CREATE TRIGGER block_event_update BEFORE UPDATE ON review_events "
                        "BEGIN SELECT RAISE(ABORT,'review events are append only'); END")
            con.execute("CREATE TRIGGER block_event_delete BEFORE DELETE ON review_events "
                        "BEGIN SELECT RAISE(ABORT,'review events are append only'); END")
            con.execute("CREATE TRIGGER block_meta_update BEFORE UPDATE ON journal_meta "
                        "BEGIN SELECT RAISE(ABORT,'journal metadata is write locked'); END")
            con.execute("CREATE TRIGGER block_meta_delete BEFORE DELETE ON journal_meta "
                        "BEGIN SELECT RAISE(ABORT,'journal metadata is write locked'); END")
            con.execute("INSERT INTO journal_meta VALUES (1,?,?,?)",
                        (JOURNAL_SCHEMA, packet["packet_sha256"], _canonical(packet)))
    return packet["packet_sha256"]


def _verify(con: sqlite3.Connection, key: bytes, expected_tip: str | None) -> dict:
    if con.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        raise ValueError("SQLite integrity check failed")
    meta = con.execute(
        "SELECT schema_version,packet_sha256,packet_json FROM journal_meta WHERE singleton=1"
    ).fetchone()
    if meta is None or meta[0] != JOURNAL_SCHEMA:
        raise ValueError("Journal metadata invalid")
    packet = json.loads(meta[2])
    targets = _packet_checked(packet)
    if meta[1] != packet["packet_sha256"]:
        raise ValueError("Journal packet reference mismatch")
    last_digest = GENESIS
    last_seq = 0
    events = []
    for seq, serialized, recorded_sha, recorded_hmac in con.execute(
            "SELECT seq,event_json,event_sha256,hmac_sha256 "
            "FROM review_events ORDER BY seq"):
        if type(seq) is not int or seq != last_seq + 1:
            raise ValueError("Missing or out-of-order review event")
        event = json.loads(serialized)
        if _canonical(event) != serialized:
            raise ValueError("Noncanonical journal event")
        if (event.get("schema") != JOURNAL_SCHEMA or event.get("seq") != seq
                or event.get("packet_sha256") != meta[1]
                or event.get("previous_sha256") != last_digest
                or event.get("component_id") not in targets
                or event.get("evidence_sha256")
                != targets[event["component_id"]]["evidence_sha256"]
                or event.get("decision") not in DECISIONS
                or not isinstance(event.get("reason"), str)
                or not 10 <= len(event["reason"].strip()) <= 1000
                or not isinstance(event.get("reviewer_id"), str)
                or ACTOR.fullmatch(event["reviewer_id"]) is None
                or not isinstance(event.get("recorded_utc"), str)
                or not isinstance(event.get("key_id"), str)
                or ACTOR.fullmatch(event["key_id"]) is None):
            raise ValueError("Invalid or forged review event fields")
        actual = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        if (not isinstance(recorded_sha, str)
                or not hmac.compare_digest(actual, recorded_sha)
                or not isinstance(recorded_hmac, str)
                or not hmac.compare_digest(_signature(key, actual), recorded_hmac)):
            raise ValueError("Review event integrity or HMAC check failed")
        last_digest, last_seq = actual, seq
        events.append({"event": event, "event_sha256": actual,
                       "hmac_sha256": recorded_hmac})
    if expected_tip is not None:
        if HEX64.fullmatch(expected_tip) is None or not hmac.compare_digest(
                expected_tip, last_digest):
            raise ValueError("External head anchor does not match this journal")
    return {
        "schema": JOURNAL_SCHEMA,
        "packet_sha256": meta[1],
        "event_count": last_seq,
        "head_sha256": last_digest,
        "externally_anchored": expected_tip is not None,
        "verification": "LOCAL_HMAC_INTEGRITY_ONLY_NOT_AUTHENTICATED_IDENTITY",
        "external_release_authorized": False,
        "events": events,
    }


def verify(db: Path, key: bytes, expected_tip: str | None = None) -> dict:
    """Verify local event chain, symmetric HMAC, and optional retained head anchor."""
    if not isinstance(key, bytes) or len(key) < 32:
        raise ValueError("Signing key must contain at least 32 bytes")
    if db.is_symlink() or not db.is_file():
        raise FileNotFoundError("Journal not found or symlink disallowed")
    with closing(sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True)) as con:
        return _verify(con, key, expected_tip)


def record(db: Path, *, component_id: str, reviewer_id: str,
           decision: str, reason: str, key_id: str,
           key: bytes) -> dict:
    """Append one HMAC-linked *research-only* event after verifying prior events."""
    if (not isinstance(key, bytes) or len(key) < 32
            or not isinstance(reviewer_id, str) or ACTOR.fullmatch(reviewer_id) is None
            or not isinstance(key_id, str) or ACTOR.fullmatch(key_id) is None
            or decision not in DECISIONS
            or not isinstance(reason, str) or not 10 <= len(reason.strip()) <= 1000
            or not isinstance(component_id, str) or not component_id):
        raise ValueError("Invalid reviewer, key, disposition or documented reason")
    if db.is_symlink() or not db.is_file():
        raise FileNotFoundError("Journal not found or symlink disallowed")
    with closing(sqlite3.connect(db)) as con:
        con.execute("BEGIN IMMEDIATE")
        status = _verify(con, key, None)
        packet_json = con.execute("SELECT packet_json FROM journal_meta WHERE singleton=1").fetchone()[0]
        packet = json.loads(packet_json)
        targets = _packet_checked(packet)
        if component_id not in targets:
            raise ValueError("Component is not in the research review queue")
        event = {
            "schema": JOURNAL_SCHEMA,
            "packet_sha256": status["packet_sha256"],
            "seq": status["event_count"] + 1,
            "previous_sha256": status["head_sha256"],
            "component_id": component_id,
            "evidence_sha256": targets[component_id]["evidence_sha256"],
            "reviewer_id": reviewer_id,
            "decision": decision,
            "reason": reason.strip(),
            "key_id": key_id,
            "recorded_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        serialized = _canonical(event)
        event_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        signature = _signature(key, event_hash)
        con.execute("INSERT INTO review_events VALUES (?,?,?,?)",
                    (event["seq"], serialized, event_hash, signature))
        con.commit()
    return {"sequence": event["seq"], "event_sha256": event_hash,
            "journal_head_sha256": event_hash, "packet_sha256": status["packet_sha256"],
            "disposition": decision, "external_release_authorized": False}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Local synthetic AeroCIE research review register")
    commands = parser.add_subparsers(dest="action", required=True)
    init = commands.add_parser("init")
    init.add_argument("--db", required=True, type=Path)
    init.add_argument("--packet", required=True, type=Path)
    submit = commands.add_parser("record")
    submit.add_argument("--db", required=True, type=Path)
    submit.add_argument("--component", required=True)
    submit.add_argument("--reviewer", required=True)
    submit.add_argument("--decision", required=True, choices=DECISIONS)
    submit.add_argument("--reason", required=True)
    submit.add_argument("--key-id", required=True)
    check = commands.add_parser("verify")
    check.add_argument("--db", required=True, type=Path)
    check.add_argument("--expected-head")
    args = parser.parse_args(argv)
    try:
        if args.action == "init":
            from .prime_adapters import load_json
            result = {"packet_sha256": initialize(args.db, load_json(args.packet)),
                      "status": "SYNTHETIC_ONLY_NOT_RELEASED"}
        elif args.action == "record":
            result = record(args.db, component_id=args.component,
                            reviewer_id=args.reviewer, decision=args.decision,
                            reason=args.reason, key_id=args.key_id,
                            key=_key_from_env())
        else:
            result = verify(args.db, _key_from_env(), args.expected_head)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (ValueError, OSError, sqlite3.Error, TypeError) as exc:
        parser.exit(2, f"Research journal error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
