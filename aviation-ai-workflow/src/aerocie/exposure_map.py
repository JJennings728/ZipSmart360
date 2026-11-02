"""AeroCIE-012 | Offline aviation regulatory research-exposure candidates.

A manually proposed association between a synthetic/internal aviation subject
and published source metadata. Never determines legal applicability, exposure,
regulatory effect, insured risk or release approval.
"""
from __future__ import annotations

import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys

from .knowledge_graph import checked, check_id, evidence_edges
from .reviewer_packet import snapshot

DEFAULT_DB = Path("build/aerocie/exposure_candidates.sqlite3")
DEFAULT_SOURCE_DB = Path("build/aerocie/federal_register.sqlite3")
DEFAULT_GRAPH_DB = Path("build/aerocie/knowledge_graph.sqlite3")
SUBJECT_TYPES = ("FACILITY", "AIRCRAFT", "COMPONENT", "OPERATION")
DOC_RE = re.compile(r"^\d{4}-\d{4,6}$")
PIN_OK = "LOCAL_BOTH_METADATA_PINS_MATCH_ONLY_NOT_CURRENT_AUTHORITY"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _read_only(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise ValueError("Required local evidence database is unavailable")
    conn = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _guard(db: Path, source_db: Path, graph_db: Path) -> None:
    paths = (db.resolve(), source_db.resolve(), graph_db.resolve())
    if len(set(paths)) != len(paths):
        raise ValueError("Exposure, collector and knowledge graph databases must be distinct")
    for other in (source_db, graph_db):
        if db.exists() and other.exists() and db.samefile(other):
            raise ValueError("Refusing to write into a source or graph database")
    if db.is_file():
        with closing(_read_only(db)) as conn:
            tables = {row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
        if tables.intersection(("document_snapshots", "change_events", "kg_documents",
                                "kg_nodes", "kg_edges", "obligation_candidates")):
            raise ValueError("Refusing to write into an existing research evidence database")


def _connect(db: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def initialize(db: Path, source_db: Path = DEFAULT_SOURCE_DB,
               graph_db: Path = DEFAULT_GRAPH_DB) -> None:
    _guard(db, source_db, graph_db)
    db.parent.mkdir(parents=True, exist_ok=True)
    with closing(_connect(db)) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS exposure_subjects(
                subject_id TEXT PRIMARY KEY,
                subject_type TEXT NOT NULL,
                label TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS exposure_candidates(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id TEXT NOT NULL REFERENCES exposure_subjects(subject_id),
                document_number TEXT NOT NULL,
                graph_document_id TEXT NOT NULL,
                source_sha256 TEXT NOT NULL,
                exact_excerpt TEXT NOT NULL,
                rationale TEXT NOT NULL,
                locator TEXT NOT NULL,
                researcher TEXT NOT NULL,
                recorded_at TEXT NOT NULL,
                research_state TEXT NOT NULL DEFAULT 'PROPOSED_RESEARCH_ONLY'
                    CHECK (research_state='PROPOSED_RESEARCH_ONLY'),
                UNIQUE(subject_id, graph_document_id, exact_excerpt)
            );
            CREATE INDEX IF NOT EXISTS exposure_candidate_doc
                ON exposure_candidates(document_number);
        """)
        conn.commit()


def add_subject(db: Path, *, subject_id: str, subject_type: str, label: str,
                source_db: Path = DEFAULT_SOURCE_DB,
                graph_db: Path = DEFAULT_GRAPH_DB) -> dict:
    subject_id = check_id(subject_id)
    if subject_type not in SUBJECT_TYPES:
        raise ValueError("Unsupported research subject type")
    label = checked(label, "Research subject label", 160)
    initialize(db, source_db, graph_db)
    with closing(_connect(db)) as conn:
        with conn:
            prior = conn.execute(
                "SELECT subject_type,label FROM exposure_subjects WHERE subject_id=?",
                (subject_id,)).fetchone()
            if prior:
                if (prior["subject_type"], prior["label"]) != (subject_type, label):
                    raise ValueError("Research subject cannot be silently redefined")
                return {"subject_id": subject_id, "event": "existing_same_subject"}
            conn.execute(
                "INSERT INTO exposure_subjects(subject_id,subject_type,label,created_at)"
                " VALUES (?,?,?,?)", (subject_id, subject_type, label, _utc_now()))
    return {"subject_id": subject_id, "event": "created"}


def _require_graph_document(graph_db: Path, number: str, expected_sha: str,
                            excerpt: str) -> str:
    with closing(_read_only(graph_db)) as conn:
        node = conn.execute(
            "SELECT kind FROM kg_nodes WHERE id=?", ("frdoc:" + number,)
        ).fetchone()
        if not node or node["kind"] != "PUBLICATION":
            raise ValueError("Referenced PUBLICATION node not in research graph")
        records = conn.execute(
            "SELECT id,content,sha256 FROM kg_documents "
            "WHERE kind='FR_METADATA' AND source_doc_number=? AND sha256=?",
            (number, expected_sha)).fetchall()
    if len(records) != 1:
        raise ValueError("Current pinned published metadata not imported into graph")
    record = records[0]
    if _digest(record["content"]) != expected_sha:
        raise ValueError("Graph document evidence integrity mismatch")
    if excerpt not in record["content"]:
        raise ValueError("Exact supporting excerpt is absent from pinned document")
    return record["id"]


def propose(db: Path, *, subject_id: str, document_number: str,
            excerpt: str, rationale: str, locator: str, researcher: str,
            source_db: Path = DEFAULT_SOURCE_DB,
            graph_db: Path = DEFAULT_GRAPH_DB) -> dict:
    subject_id = check_id(subject_id)
    if not isinstance(document_number, str) or not DOC_RE.fullmatch(document_number):
        raise ValueError("Expected a Federal Register publication number")
    excerpt = checked(excerpt, "Exact source excerpt", 1500)
    rationale = checked(rationale, "Research rationale", 1200)
    if len(rationale) < 20:
        raise ValueError("Record a substantive research rationale (20+ characters)")
    locator = checked(locator, "Human supplied source locator", 240)
    researcher = checked(researcher, "Researcher", 120)
    _guard(db, source_db, graph_db)
    pin = snapshot(source_db, document_number)
    doc_id = _require_graph_document(
        graph_db, document_number, pin["fingerprint"], excerpt)
    initialize(db, source_db, graph_db)
    with closing(_connect(db)) as conn:
        with conn:
            if not conn.execute(
                "SELECT 1 FROM exposure_subjects WHERE subject_id=?",
                (subject_id,)).fetchone():
                raise ValueError("Research subject must be recorded first")
            cur = conn.execute(
                """INSERT INTO exposure_candidates
                   (subject_id,document_number,graph_document_id,source_sha256,
                    exact_excerpt,rationale,locator,researcher,recorded_at)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (subject_id, document_number, doc_id, pin["fingerprint"], excerpt,
                 rationale, locator, researcher, _utc_now()))
    return {"candidate_id": cur.lastrowid,
            "research_state": "PROPOSED_RESEARCH_ONLY",
            "applicability_status": "NOT_DETERMINED"}


def _candidate_evidence_status(row: dict, source_db: Path,
                               graph_db: Path) -> str:
    try:
        pinned = snapshot(source_db, row["document_number"],
                          fingerprint=row["source_sha256"])
    except (ValueError, OSError, sqlite3.Error, TypeError):
        return "PINNED_SOURCE_UNAVAILABLE_OR_INVALID"
    if pinned["fingerprint"] != row["source_sha256"]:
        return "PINNED_SOURCE_UNAVAILABLE_OR_INVALID"
    try:
        latest = snapshot(source_db, row["document_number"])
    except (ValueError, OSError, sqlite3.Error, TypeError):
        return "LATEST_LOCAL_SOURCE_UNAVAILABLE"
    if latest["fingerprint"] != row["source_sha256"]:
        return "NEWER_LOCAL_METADATA_REQUIRES_REVIEW"
    try:
        with closing(_read_only(graph_db)) as conn:
            doc = conn.execute(
                "SELECT id,kind,source_doc_number,content,sha256 FROM kg_documents "
                "WHERE id=?", (row["graph_document_id"],)).fetchone()
            node = conn.execute("SELECT kind FROM kg_nodes WHERE id=?",
                                ("frdoc:" + row["document_number"],)).fetchone()
        if not doc or not node or node["kind"] != "PUBLICATION":
            return "GRAPH_PUBLICATION_EVIDENCE_UNAVAILABLE"
        if (doc["kind"] != "FR_METADATA"
                or doc["source_doc_number"] != row["document_number"]
                or doc["sha256"] != row["source_sha256"]
                or not isinstance(doc["content"], str)
                or _digest(doc["content"]) != row["source_sha256"]):
            return "GRAPH_DOCUMENT_INTEGRITY_FAILURE"
        if row["exact_excerpt"] not in doc["content"]:
            return "PINNED_SOURCE_EXCERPT_MISSING"
    except (ValueError, OSError, sqlite3.Error, TypeError):
        return "GRAPH_PUBLICATION_EVIDENCE_UNAVAILABLE"
    return "LOCAL_SOURCE_PIN_MATCH_ONLY_NOT_APPLICABILITY"


def export_candidates(db: Path, source_db: Path = DEFAULT_SOURCE_DB,
                      graph_db: Path = DEFAULT_GRAPH_DB) -> dict:
    _guard(db, source_db, graph_db)
    if not db.is_file():
        candidates = []
        subjects = []
    else:
        with closing(_read_only(db)) as conn:
            subjects = [dict(r) for r in conn.execute(
                "SELECT * FROM exposure_subjects ORDER BY subject_id")]
            candidates = [dict(r) for r in conn.execute(
                """SELECT e.*,s.subject_type,s.label AS subject_label
                   FROM exposure_candidates e JOIN exposure_subjects s
                   ON e.subject_id=s.subject_id ORDER BY e.id""")]
    # Evidence edges are graph-local research candidates, not a complete
    # search for FAA amendments; absence never means none exist.
    try:
        correction_edges = [
            edge for edge in evidence_edges(graph_db, source_db)
            if edge["predicate"] == "CORRECTS"
        ] if graph_db.is_file() else []
        graph_status = "LOCAL_GRAPH_INSPECTED_NOT_CURRENT_AUTHORITY" if graph_db.is_file() else "GRAPH_NOT_AVAILABLE"
    except (ValueError, OSError, sqlite3.Error, TypeError):
        correction_edges = []
        graph_status = "GRAPH_EVIDENCE_INSPECTION_FAILED_REQUIRES_REVIEW"
    for item in candidates:
        item["evidence_status"] = _candidate_evidence_status(
            item, source_db, graph_db)
        related = [
            edge for edge in correction_edges if item["document_number"] in
            (edge["from_id"].removeprefix("frdoc:"),
             edge["to_id"].removeprefix("frdoc:"))
        ]
        item["related_local_correction_candidates"] = len(related)
        item["correction_evidence_statuses"] = [
            edge["evidence_status"] for edge in related
        ]
        item["requires_review"] = (
            item["evidence_status"] != "LOCAL_SOURCE_PIN_MATCH_ONLY_NOT_APPLICABILITY"
            or any(edge["evidence_status"] != PIN_OK for edge in related)
            or graph_status == "GRAPH_EVIDENCE_INSPECTION_FAILED_REQUIRES_REVIEW"
        )
        item["applicability_status"] = "NOT_DETERMINED"
        item["operational_exposure_status"] = "NOT_DETERMINED"
        item["human_review_complete"] = False
        item["external_release_authorized"] = False
    return {
        "module": "AeroCIE-012",
        "scope": "OFFLINE_RESEARCH_ASSOCIATIONS_ONLY",
        "subjects": subjects,
        "candidates": candidates,
        "graph_status": graph_status,
        "compliance_status": "NOT_DETERMINED",
        "human_review_complete": False,
        "external_release_authorized": False,
        "limitations": (
            "Candidate associations are manually entered relevance hypotheses "
            "only. No claim of FAA applicability, effective legal status, asset "
            "exposure, insured loss, compliance or release authorization. "
            "Collector and graph snapshots are local, not authenticated "
            "current authority; no complete amendment or source coverage."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="AeroCIE-012 offline aviation research-exposure candidates")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--source-db", type=Path, default=DEFAULT_SOURCE_DB)
    parser.add_argument("--graph-db", type=Path, default=DEFAULT_GRAPH_DB)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("init")
    subject = sub.add_parser("add-subject")
    subject.add_argument("--subject-id", required=True)
    subject.add_argument("--type", choices=SUBJECT_TYPES, required=True)
    subject.add_argument("--label", required=True)
    link = sub.add_parser("propose")
    link.add_argument("--subject-id", required=True)
    link.add_argument("--document-number", required=True)
    link.add_argument("--excerpt", required=True)
    link.add_argument("--rationale", required=True)
    link.add_argument("--locator", required=True)
    link.add_argument("--researcher", required=True)
    sub.add_parser("export")
    args = parser.parse_args(argv)
    try:
        if args.action == "init":
            initialize(args.db, args.source_db, args.graph_db)
            result = {"database": str(args.db)}
        elif args.action == "add-subject":
            result = add_subject(
                args.db, subject_id=args.subject_id,
                subject_type=args.type, label=args.label,
                source_db=args.source_db, graph_db=args.graph_db)
        elif args.action == "propose":
            result = propose(
                args.db, subject_id=args.subject_id,
                document_number=args.document_number, excerpt=args.excerpt,
                rationale=args.rationale, locator=args.locator,
                researcher=args.researcher, source_db=args.source_db,
                graph_db=args.graph_db)
        else:
            result = export_candidates(args.db, args.source_db, args.graph_db)
        print(json.dumps({
            "compliance_status": "NOT_DETERMINED",
            "external_release_authorized": False,
            "result": result,
        }, indent=2, ensure_ascii=False))
        return 0
    except (ValueError, OSError, sqlite3.Error, UnicodeError) as exc:
        print("AeroCIE-012 research error:", exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
