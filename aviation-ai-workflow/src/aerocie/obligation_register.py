"""AeroCIE-008 | Local candidate-obligation register.

Research-triage prototype only. Never determines compliance, legal applicability,
airworthiness, or authorizes a client deliverable. No API key, hosted service,
login, auto-generated obligation, or customer data is required.
"""
from __future__ import annotations

import argparse
from contextlib import closing
from datetime import date, datetime, timezone
import json
from pathlib import Path
import sqlite3
import sys
import uuid

from .reviewer_packet import snapshot

DEFAULT_DB = Path("build/aerocie/obligation_candidates.sqlite3")
DEFAULT_SOURCE_DB = Path("build/aerocie/federal_register.sqlite3")
STATES = ("RESEARCH_CANDIDATE", "UNDER_RESEARCH_REVIEW",
          "RESEARCH_HOLD", "ARCHIVED_RESEARCH_ONLY")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def initialize(db: Path) -> None:
    db.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(db)) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS obligation_candidates (
              id TEXT PRIMARY KEY,
              source_document TEXT NOT NULL,
              source_fingerprint TEXT NOT NULL,
              source_url TEXT NOT NULL,
              research_question TEXT NOT NULL,
              owner TEXT NOT NULL DEFAULT '',
              internal_review_by TEXT,
              status TEXT NOT NULL DEFAULT 'RESEARCH_CANDIDATE',
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS candidate_events (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              candidate_id TEXT NOT NULL REFERENCES obligation_candidates(id),
              event TEXT NOT NULL,
              actor TEXT NOT NULL,
              notes TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS candidate_events_lookup
              ON candidate_events(candidate_id, id);
        """)
        conn.commit()


def _checked_text(value: str, label: str, limit: int = 1000) -> str:
    value = value.strip()
    if not value or len(value) > limit or any(ord(c) < 32 and c not in "\n\t" for c in value):
        raise ValueError(f"{label} is required (1–{limit} printable characters)")
    return value


def add_candidate(db: Path, source_db: Path, *, document_number: str,
                  research_question: str, actor: str, owner: str = "",
                  internal_review_by: str | None = None) -> dict:
    question = _checked_text(research_question, "Research question", 1500)
    actor = _checked_text(actor, "Actor", 120)
    if len(owner) > 120:
        raise ValueError("Owner too long")
    if internal_review_by:
        date.fromisoformat(internal_review_by)
    # A pinned SOURCE snapshot is a research lead, never an obligation decision.
    source = snapshot(source_db, document_number)
    record = source["record"]
    source_url = record.get("html_url") or ""
    if not isinstance(source_url, str) or not source_url.startswith("https://www.federalregister.gov/"):
        raise ValueError("Unexpected source URL: only Federal Register HTTPS supported")
    candidate_id = uuid.uuid4().hex
    now = utc_now()
    initialize(db)
    with closing(sqlite3.connect(db)) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        with conn:
            conn.execute("""INSERT INTO obligation_candidates
                (id, source_document, source_fingerprint, source_url,
                 research_question, owner, internal_review_by, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (candidate_id, document_number, source["fingerprint"], source_url,
                 question, owner.strip(), internal_review_by, STATES[0], now))
            conn.execute("""INSERT INTO candidate_events
                (candidate_id, event, actor, notes, created_at)
                VALUES (?, 'candidate_created', ?, ?, ?)""",
                (candidate_id, actor, "Candidate only | qualified review required", now))
    return {"id": candidate_id, "state": STATES[0],
            "source_document": document_number, "review_required": True,
            "compliance_status": "NOT_DETERMINED"}


def change_research_status(db: Path, *, candidate_id: str, state: str,
                           actor: str, notes: str) -> dict:
    if state not in STATES[1:]:
        raise ValueError("Only research workflow states are allowed; no compliance approval")
    actor = _checked_text(actor, "Actor", 120)
    notes = _checked_text(notes, "Review notes", 3000)
    initialize(db)
    with closing(sqlite3.connect(db)) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        with conn:
            row = conn.execute("SELECT status FROM obligation_candidates WHERE id=?",
                               (candidate_id,)).fetchone()
            if row is None:
                raise ValueError("Candidate ID not found")
            conn.execute("UPDATE obligation_candidates SET status=? WHERE id=?",
                         (state, candidate_id))
            conn.execute("""INSERT INTO candidate_events
                (candidate_id, event, actor, notes, created_at)
                VALUES (?, ?, ?, ?, ?)""",
                (candidate_id, f"{row[0]} -> {state}", actor, notes, utc_now()))
    return {"id": candidate_id, "research_state": state,
            "compliance_status": "NOT_DETERMINED"}


def candidates(db: Path, source_db: Path | None = None) -> list[dict]:
    if not db.is_file():
        return []
    with closing(sqlite3.connect(f"file:{db.resolve().as_posix()}?mode=ro", uri=True)) as conn:
        conn.row_factory = sqlite3.Row
        rows = [dict(r) for r in conn.execute(
            "SELECT * FROM obligation_candidates ORDER BY created_at DESC, id")]
        for row in rows:
            row["compliance_status"] = "NOT_DETERMINED"
            row["external_release_authorized"] = False
            row["source_status"] = "NOT_RECHECKED"
            if source_db is not None:
                try:
                    current = snapshot(source_db, row["source_document"])
                    row["source_status"] = ("SOURCE_SNAPSHOT_CURRENT"
                                            if current["fingerprint"] == row["source_fingerprint"]
                                            else "SOURCE_CHANGED_REVIEW_REQUIRED")
                except (ValueError, FileNotFoundError, sqlite3.Error):
                    row["source_status"] = "SOURCE_UNAVAILABLE_REVIEW_REQUIRED"
    return rows


def events(db: Path, candidate_id: str) -> list[dict]:
    if not db.is_file():
        return []
    with closing(sqlite3.connect(f"file:{db.resolve().as_posix()}?mode=ro", uri=True)) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(r) for r in conn.execute(
            "SELECT * FROM candidate_events WHERE candidate_id=? ORDER BY id",
            (candidate_id,))]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AeroCIE-008 local research candidate register")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--source-db", type=Path, default=DEFAULT_SOURCE_DB)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init")
    add = commands.add_parser("add-from-faa")
    add.add_argument("--document-number", required=True)
    add.add_argument("--question", required=True, help="Research question, NOT a verified legal obligation")
    add.add_argument("--actor", required=True)
    add.add_argument("--owner", default="")
    add.add_argument("--review-by", help="Internal target date; NOT a statutory due date")
    change = commands.add_parser("status")
    change.add_argument("--id", required=True)
    change.add_argument("--state", required=True, choices=STATES[1:])
    change.add_argument("--actor", required=True)
    change.add_argument("--notes", required=True)
    commands.add_parser("list")
    history = commands.add_parser("history")
    history.add_argument("--id", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            initialize(args.db)
            result = {"database": str(args.db), "status": "initialized_local_only"}
        elif args.command == "add-from-faa":
            result = add_candidate(args.db, args.source_db,
                document_number=args.document_number, research_question=args.question,
                actor=args.actor, owner=args.owner, internal_review_by=args.review_by)
        elif args.command == "status":
            result = change_research_status(args.db, candidate_id=args.id,
                state=args.state, actor=args.actor, notes=args.notes)
        elif args.command == "history":
            result = events(args.db, args.id)
        else:
            result = candidates(args.db, args.source_db)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except (ValueError, sqlite3.Error, OSError) as exc:
        print(f"AeroCIE-008 error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
