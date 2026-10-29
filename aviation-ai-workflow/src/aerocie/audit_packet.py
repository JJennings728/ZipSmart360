"""AeroCIE-013: unsigned offline regulatory research review packet."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import re
import sqlite3
import sys
from urllib.parse import urlsplit
from .effective_dates import build_timeline, parse_date
from .exposure_map import export_candidates
from .reviewer_packet import DEFAULT_REVIEWS, find_current_review

DOC_RE = re.compile(r"^\d{4}-\d{4,6}$")
GOOD_CANDIDATE = "LOCAL_SOURCE_PIN_MATCH_ONLY_NOT_APPLICABILITY"
GOOD_CORRECTION = "LOCAL_BOTH_METADATA_PINS_MATCH_ONLY_NOT_CURRENT_AUTHORITY"
CHECKS = (
    ("source_text", "Independently verify the official Federal Register publication and complete governing text."),
    ("faa_drs", "Cross-check current FAA DRS and agency guidance; note source access date."),
    ("correction_pins", "Review original and correcting publications, exact excerpts and both source fingerprints."),
    ("later_changes", "Check later amendments, suspensions, delays, supersession and incorporated materials."),
    ("operative_date", "Verify operative effective-date clauses and exceptions, not metadata dates alone."),
    ("subject_facts", "Verify actual facility, aircraft, component or operational facts using independent evidence."),
    ("applicability", "Document any subject-specific applicability analysis, authoritative citations and limitations."),
    ("integrity", "Reconcile stale source versions, tampered records and invalid self-attested review receipts."),
)


def _sha(value: dict) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")).hexdigest()


def verify_packet_hash(packet: dict) -> bool:
    if not isinstance(packet, dict):
        return False
    digest = packet.get("audit_sha256")
    return (isinstance(digest, str) and bool(re.fullmatch(r"[0-9a-f]{64}", digest))
            and digest == _sha({k: v for k, v in packet.items() if k != "audit_sha256"}))


def _official_url(url: object) -> str | None:
    if not isinstance(url, str) or any(ord(c) < 33 for c in url):
        return None
    try:
        parsed = urlsplit(url)
        if (parsed.scheme != "https"
                or parsed.hostname != "www.federalregister.gov"
                or parsed.port not in (None, 443)
                or parsed.username or parsed.password
                or not parsed.path.startswith("/documents/")):
            return None
    except ValueError:
        return None
    return url


def build_packet(registry_db: Path, source_db: Path, graph_db: Path, *,
                 candidate_id: int, as_of: str | None = None,
                 reviews_dir: Path = DEFAULT_REVIEWS) -> dict:
    if type(candidate_id) is not int or candidate_id <= 0:
        raise ValueError("Candidate ID must be positive integer")
    as_of = as_of or datetime.now(timezone.utc).date().isoformat()
    if parse_date(as_of)[1] != "METADATA_DATE_ONLY":
        raise ValueError("Invalid as-of date")
    dbs = (registry_db, source_db, graph_db)
    if not all(x.is_file() for x in dbs) or len({x.resolve() for x in dbs}) != 3:
        raise ValueError("Require three distinct existing local research databases")
    registry = export_candidates(registry_db, source_db, graph_db)
    matched = [c for c in registry["candidates"] if c["id"] == candidate_id]
    if len(matched) != 1:
        raise ValueError("Candidate not found")
    candidate = matched[0]
    number = candidate["document_number"]
    if not isinstance(number, str) or not DOC_RE.fullmatch(number):
        raise ValueError("Invalid candidate publication")
    timeline = build_timeline(source_db, graph_db,
                              document_numbers=[number], as_of=as_of)
    relations = timeline["correction_candidates"]
    numbers = {number}
    for relation in relations:
        numbers.add(relation["correcting_document_number"])
        numbers.add(relation["earlier_document_number"])
    documents, missing = [], []
    for target in sorted(numbers):
        if not isinstance(target, str) or not DOC_RE.fullmatch(target):
            raise ValueError("Invalid related publication")
        try:
            timeline_doc = build_timeline(source_db, graph_db,
                                          document_numbers=[target], as_of=as_of)
            documents.extend(timeline_doc["documents"])
        except (ValueError, OSError, sqlite3.Error, TypeError):
            if target == number:
                raise
            missing.append(target)
    for doc in documents:
        doc["official_link_format_checked_only"] = _official_url(
            doc.pop("federal_register_url", None))
        doc["local_self_attested_source_review"] = find_current_review(
            reviews_dir, doc["document_number"], doc["source_sha256"])
        doc["human_review_complete"] = False
    events = []
    for doc in documents:
        for label, key in (
            ("PUBLISHED_METADATA_DATE", "publication_date"),
            ("STATED_EFFECTIVE_METADATA_DATE", "stated_effective_on"),
        ):
            if doc.get(key):
                events.append({
                    "date": doc[key], "event_type": label,
                    "document_number": doc["document_number"],
                    "legal_effect_determined": False,
                })
    events.sort(key=lambda row: (row["date"], row["event_type"], row["document_number"]))
    degraded = (
        candidate["evidence_status"] != GOOD_CANDIDATE
        or candidate.get("requires_review") is True
        or bool(missing)
        or timeline["graph_status"] != "LOCAL_GRAPH_INSPECTED_NOT_CURRENT_AUTHORITY"
        or any(edge["evidence_status"] != GOOD_CORRECTION for edge in relations)
        or any(doc["source_integrity_status"]
               != "LOCAL_METADATA_PINS_MATCH_NOT_CURRENT_AUTHORITY"
               or doc["publication_date_status"] != "METADATA_DATE_ONLY"
               or doc["effective_date_status"] != "METADATA_DATE_ONLY"
               or doc["local_self_attested_source_review"]["state"]
                  == "integrity_problem_requires_review"
               for doc in documents)
    )
    packet = {
        "packet_schema": "AEROCIE-013-UNSIGNED-RESEARCH-DRAFT-v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "as_of_calendar_date": as_of,
        "candidate_id": candidate_id,
        "research_candidate": candidate,
        "published_metadata_documents": documents,
        "timeline_events_metadata_only": events,
        "correction_candidates_research_only": relations,
        "missing_related_publications": missing,
        "graph_status": timeline["graph_status"],
        "source_integrity_or_refresh_review_needed": bool(degraded),
        "human_review_checklist": [
            {"check_id": key, "instruction": prompt, "status": "PENDING_HUMAN_REVIEW",
             "verified_citation": None, "notes": None} for key, prompt in CHECKS
        ],
        "review_disposition": "HOLD_FOR_HUMAN_REVIEW",
        "reviewer_name": None,
        "reviewer_role": None,
        "review_signed_at": None,
        "human_review_complete": False,
        "applicability_status": "NOT_DETERMINED",
        "operational_exposure_status": "NOT_DETERMINED",
        "compliance_status": "NOT_DETERMINED",
        "external_release_authorized": False,
        "limitations": (
            "Unsigned research preparation only. Local hashes do not authenticate "
            "current government source authority. No complete amendment history, "
            "actual operative effective date, asset-specific FAA applicability, "
            "insured exposure or client-release authorization is established. "
            "Existing source-review receipts are local self-attestations only."
        ),
    }
    packet["audit_sha256"] = _sha(packet)
    return packet


def render_html(packet: dict) -> str:
    if not verify_packet_hash(packet):
        raise ValueError("Unsigned packet digest mismatch")
    def esc(value: object) -> str:
        return html.escape("" if value is None else str(value), quote=True)
    candidate = packet["research_candidate"]
    sections = []
    for d in packet["published_metadata_documents"]:
        url = d.get("official_link_format_checked_only")
        link = (f'<a href="{esc(url)}" rel="noopener noreferrer">Official source'
                ' (verify independently)</a>' if _official_url(url)
                else "Official source link unavailable")
        sections.append(
            "<section class='sheet'><h3>" + esc(d["document_number"])
            + " | " + esc(d.get("title")) + "</h3><p>Published: "
            + esc(d.get("publication_date")) + " | Stated effective: "
            + esc(d.get("stated_effective_on")) + "</p><p>SHA-256: <code>"
            + esc(d.get("source_sha256")) + "</code></p><p>Local status: "
            + esc(d.get("source_integrity_status")) + " | Source receipt: "
            + esc(d["local_self_attested_source_review"].get("state"))
            + "</p><p>" + link + "</p></section>"
        )
    corrections = "".join(
        "<li>" + esc(e["correcting_document_number"]) + " CORRECTS "
        + esc(e["earlier_document_number"]) + " | "
        + esc(e["evidence_status"]) + " | PROPOSED_RESEARCH_ONLY</li>"
        for e in packet["correction_candidates_research_only"]
    ) or "<li>None indexed locally; completeness has not been established.</li>"
    checks = "".join(
        "<li><strong>" + esc(x["check_id"]) + "</strong> "
        + esc(x["instruction"]) + " [" + esc(x["status"]) + "]</li>"
        for x in packet["human_review_checklist"]
    )
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<title>SRP | AeroCIE-013 Evidence Review Packet</title>"
        "<style>body{font:14px/1.6 Arial,sans-serif;max-width:900px;"
        "margin:auto;padding:30px;color:#15304f}header{border-bottom:4px solid #2369ad}"
        ".sheet{border:1px solid #b6c7db;border-radius:8px;padding:15px;"
        "margin:12px 0}code{overflow-wrap:anywhere}li{margin:9px 0}"
        "a{color:#145c9b}.notice{padding:14px;background:#edf2f8}"
        "@media print{body{padding:0;max-width:none}.sheet{break-inside:avoid}}"
        "</style></head><body><header><strong>STRATEGICRISK PARTNERS"
        " | AeroCIE-013</strong><h1>Regulatory Evidence Review Packet</h1>"
        "<p>UNSIGNED RESEARCH | NOT_DETERMINED | CLIENT RELEASE NOT AUTHORIZED"
        "</p></header><p class='notice'>Research candidate only; never a "
        "finding of FAA applicability or compliance.</p><h2>Research subject</h2>"
        "<p>" + esc(candidate.get("subject_label")) + " | "
        + esc(candidate.get("subject_type")) + " | Candidate "
        + esc(packet["candidate_id"]) + "</p><p>Publication: "
        + esc(candidate.get("document_number")) + " | Evidence: "
        + esc(candidate.get("evidence_status")) + "</p><p>Rationale: "
        + esc(candidate.get("rationale")) + "</p><p>Excerpt: "
        + esc(candidate.get("exact_excerpt")) + "</p>"
        "<h2>Published metadata and source pins</h2>" + "".join(sections)
        + "<h2>Proposed correction lineage</h2><ul>" + corrections
        + "</ul><h2>Human review checklist</h2><ol>" + checks
        + "</ol><p>Disposition: " + esc(packet["review_disposition"])
        + " | Source refresh needed: "
        + esc(packet["source_integrity_or_refresh_review_needed"])
        + "</p><p>Reviewer: __________________  Role: __________________"
        "  Date: __________________</p><p>Verified citations and analysis:"
        " __________________________________________________</p><p>Packet checksum"
        " (not a trusted signature): <code>" + esc(packet["audit_sha256"])
        + "</code></p><footer>" + esc(packet["limitations"])
        + "</footer></body></html>"
    )


def write_packet(packet: dict, out_json: Path, out_html: Path, *,
                 evidence_databases: tuple[Path, Path, Path]) -> dict:
    if not verify_packet_hash(packet):
        raise ValueError("Packet checksum invalid")
    targets = (out_json.resolve(), out_html.resolve())
    sources = {p.resolve() for p in evidence_databases}
    if (targets[0] == targets[1] or any(x in sources for x in targets)
            or any(x.suffix.lower() in (".sqlite3", ".sqlite", ".db")
                   for x in targets)):
        raise ValueError("Unsafe output path")
    if out_json.exists() or out_html.exists():
        raise FileExistsError("Refusing to overwrite existing packet")
    page = render_html(packet)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_html.parent.mkdir(parents=True, exist_ok=True)
    with out_json.open("x", encoding="utf-8") as f:
        json.dump(packet, f, indent=2, ensure_ascii=False)
        f.write("\n")
    with out_html.open("x", encoding="utf-8") as f:
        f.write(page + "\n")
    return {"json_path": str(out_json), "html_path": str(out_html),
            "audit_sha256": packet["audit_sha256"],
            "review_disposition": "HOLD_FOR_HUMAN_REVIEW",
            "external_release_authorized": False}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="AeroCIE-013 offline unsigned evidence review packet")
    parser.add_argument("--registry-db", type=Path, required=True)
    parser.add_argument("--source-db", type=Path, required=True)
    parser.add_argument("--graph-db", type=Path, required=True)
    parser.add_argument("--candidate-id", type=int, required=True)
    parser.add_argument("--reviews-dir", type=Path, default=DEFAULT_REVIEWS)
    parser.add_argument("--as-of")
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--out-html", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        packet = build_packet(
            args.registry_db, args.source_db, args.graph_db,
            candidate_id=args.candidate_id, as_of=args.as_of,
            reviews_dir=args.reviews_dir)
        result = write_packet(
            packet, args.out_json, args.out_html,
            evidence_databases=(args.registry_db, args.source_db, args.graph_db))
    except (ValueError, OSError, sqlite3.Error, TypeError) as exc:
        print("AeroCIE-013 packet error:", exc, file=sys.stderr)
        return 1
    print(json.dumps({"compliance_status": "NOT_DETERMINED",
                      "external_release_authorized": False, "result": result},
                     indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
