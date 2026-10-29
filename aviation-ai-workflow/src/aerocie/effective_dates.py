"""AeroCIE-011 | Offline, research-only Federal Register date timeline.

Dates are metadata observations, not determinations of regulatory effect or
FAA applicability. Reads already-ingested local databases; never fetches.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys

from .knowledge_graph import export_graph, DEFAULT_DB as DEFAULT_GRAPH_DB
from .reviewer_packet import snapshot, DEFAULT_DB as DEFAULT_SOURCE_DB

DOC_NUMBER = re.compile(r"^\d{4}-\d{4,6}$")
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MAX_DOCUMENTS = 100
PIN_OK = "LOCAL_BOTH_METADATA_PINS_MATCH_ONLY_NOT_CURRENT_AUTHORITY"


def parse_date(value: object) -> tuple[str | None, str]:
    """Accept only an exact ISO calendar date; never invent a fallback."""
    if value is None or value == "":
        return None, "MISSING_REQUIRES_REVIEW"
    if not isinstance(value, str) or not ISO_DATE.fullmatch(value):
        return None, "INVALID_REQUIRES_REVIEW"
    try:
        dt.date.fromisoformat(value)
    except ValueError:
        return None, "INVALID_REQUIRES_REVIEW"
    return value, "METADATA_DATE_ONLY"


def date_relation(value: str | None, as_of: str) -> str:
    if value is None:
        return "UNDETERMINED"
    if value < as_of:
        return "BEFORE_AS_OF_NOT_LEGAL_STATUS"
    if value > as_of:
        return "AFTER_AS_OF_NOT_LEGAL_STATUS"
    return "ON_AS_OF_NOT_LEGAL_STATUS"


def _read_only(db: Path) -> sqlite3.Connection:
    if not db.is_file():
        raise ValueError("Missing local Federal Register collector database")
    return sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True)


def available_documents(source_db: Path, limit: int = 25) -> list[str]:
    """List most recently observed published document IDs, not proposed items."""
    if not 1 <= limit <= MAX_DOCUMENTS:
        raise ValueError("Limit must be between 1 and 100")
    with closing(_read_only(source_db)) as conn:
        rows = conn.execute(
            "SELECT document_number FROM document_snapshots "
            "WHERE source='published' GROUP BY document_number "
            "ORDER BY MAX(id) DESC LIMIT ?", (limit,)
        ).fetchall()
    return [row[0] for row in rows]


def snapshot_history(source_db: Path, number: str) -> list[dict]:
    """Track collector observations; changing metadata is not a rule amendment."""
    with closing(_read_only(source_db)) as conn:
        rows = conn.execute(
            "SELECT id,fingerprint,fetched_at,payload_json "
            "FROM document_snapshots WHERE source='published' "
            "AND document_number=? ORDER BY id", (number,)
        ).fetchall()
    result = []
    for record_id, sha, observed, raw in rows:
        integrity = "PIN_MATCH"
        try:
            if (not isinstance(raw, str) or not isinstance(sha, str)
                    or hashlib.sha256(raw.encode("utf-8")).hexdigest() != sha):
                integrity = "INVALID_FINGERPRINT_REQUIRES_REVIEW"
            else:
                record = json.loads(raw)
                if (not isinstance(record, dict)
                        or record.get("source") != "published"
                        or record.get("document_number") != number):
                    integrity = "INVALID_RECORD_REQUIRES_REVIEW"
        except (ValueError, TypeError, UnicodeError):
            integrity = "INVALID_RECORD_REQUIRES_REVIEW"
        result.append({
            "collector_snapshot_id": record_id, "observed_at": observed,
            "fingerprint_sha256": sha, "integrity": integrity,
            "regulatory_amendment_determined": False,
        })
    return result


def build_timeline(source_db: Path, graph_db: Path, *,
                   document_numbers: list[str] | None = None,
                   as_of: str | None = None, limit: int = 25) -> dict:
    """Create a metadata-only timeline; all corrections remain review candidates."""
    as_of = as_of or dt.datetime.now(dt.timezone.utc).date().isoformat()
    parsed, state = parse_date(as_of)
    if state != "METADATA_DATE_ONLY":
        raise ValueError("as_of must be a valid YYYY-MM-DD calendar date")
    if not 1 <= limit <= MAX_DOCUMENTS:
        raise ValueError("Limit must be between 1 and 100")
    requested = (available_documents(source_db, limit)
                 if document_numbers is None else document_numbers)
    if not isinstance(requested, list) or len(requested) > MAX_DOCUMENTS:
        raise ValueError("Select at most 100 document numbers")
    selected = list(dict.fromkeys(requested))
    if not all(isinstance(n, str) and DOC_NUMBER.fullmatch(n) for n in selected):
        raise ValueError("Invalid Federal Register document number")
    records = []
    events = []
    for number in selected:
        pin = snapshot(source_db, number)
        rec = pin["record"]
        pub, pub_status = parse_date(rec.get("publication_date"))
        eff, eff_status = parse_date(rec.get("effective_on"))
        history = snapshot_history(source_db, number)
        integrity = ("REVIEW_REQUIRED" if any(
            h["integrity"] != "PIN_MATCH" for h in history
        ) else "LOCAL_METADATA_PINS_MATCH_NOT_CURRENT_AUTHORITY")
        records.append({
            "document_number": number,
            "title": rec.get("title"),
            "federal_register_url": rec.get("html_url"),
            "citation": rec.get("citation"),
            "source_sha256": pin["fingerprint"],
            "source_integrity_status": integrity,
            "publication_date": pub,
            "publication_date_status": pub_status,
            "stated_effective_on": eff,
            "effective_date_status": eff_status,
            "effective_date_relative_to_as_of": date_relation(eff, parsed),
            "dates_text_uninterpreted": rec.get("dates_text"),
            "source_version_history": history,
            "formal_amendment_status": "NOT_DETERMINED",
            "applicability_status": "NOT_DETERMINED",
            "human_review_complete": False,
        })
        if pub is not None:
            events.append({"date": pub, "event_type": "PUBLISHED_METADATA_DATE",
                           "document_number": number,
                           "legal_effect_determined": False})
        if eff is not None:
            events.append({"date": eff, "event_type": "STATED_EFFECTIVE_DATE_METADATA",
                           "document_number": number,
                           "legal_effect_determined": False})
    graph_status = "GRAPH_NOT_AVAILABLE"
    correction_candidates = []
    if graph_db.is_file():
        graph_status = "LOCAL_GRAPH_INSPECTED_NOT_CURRENT_AUTHORITY"
        for edge in export_graph(graph_db, source_db)["edges"]:
            if edge["predicate"] != "CORRECTS":
                continue
            target = edge["to_id"].removeprefix("frdoc:")
            correcting = edge["from_id"].removeprefix("frdoc:")
            if target not in selected and correcting not in selected:
                continue
            evidence_status = edge["evidence_status"]
            correction_candidates.append({
                "correcting_document_number": correcting,
                "earlier_document_number": target,
                "relationship_state": "PROPOSED_RESEARCH_ONLY",
                "evidence_status": evidence_status,
                "requires_evidence_refresh": evidence_status != PIN_OK,
                "original_source_pin_sha256": edge.get("original_document_sha256"),
                "correction_source_pin_sha256": edge["document_sha256"],
                "human_review_complete": False,
                "regulatory_effect_determined": False,
            })
    events.sort(key=lambda e: (e["date"], e["event_type"], e["document_number"]))
    return {
        "module": "AeroCIE-011", "as_of": parsed,
        "scope": "OFFLINE_PUBLISHED_FEDERAL_REGISTER_METADATA_ONLY",
        "documents": records, "timeline_events": events,
        "correction_candidates": correction_candidates,
        "graph_status": graph_status,
        "formal_amendment_status": "NOT_DETERMINED",
        "compliance_status": "NOT_DETERMINED",
        "human_review_complete": False,
        "external_release_authorized": False,
        "limitations": (
            "Published metadata, source hashes and local correction candidates do not "
            "establish current authority, legal effective status, later amendments, "
            "FAA applicability, certification or permission for client release. "
            "Verify official publication text, later revisions and FAA DRS manually."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="AeroCIE-011 offline publication/effective-date research timeline")
    parser.add_argument("--source-db", type=Path, default=DEFAULT_SOURCE_DB)
    parser.add_argument("--graph-db", type=Path, default=DEFAULT_GRAPH_DB)
    parser.add_argument("--document-number", action="append", dest="document_numbers")
    parser.add_argument("--as-of", help="YYYY-MM-DD, UTC; display comparison only")
    parser.add_argument("--limit", type=int, default=25)
    args = parser.parse_args(argv)
    try:
        report = build_timeline(
            args.source_db, args.graph_db,
            document_numbers=args.document_numbers,
            as_of=args.as_of, limit=args.limit)
    except (ValueError, OSError, sqlite3.Error, TypeError) as exc:
        print(f"AeroCIE-011 research error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
