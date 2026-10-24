"""AeroCIE-007: local human source-review receipts and an internal branded packet.

NOT a compliance certification, secure signature, or client-release authorization.
Uses only Python stdlib. Does not modify the FAA collection database.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import datetime as dt
import hashlib
import html
import json
from pathlib import Path
import re
import sqlite3
import sys
import uuid
from typing import Any

from .report import safe_source_link, esc
from .review_queue import latest_documents

DOC_RE = re.compile(r"^\d{4}-\d{4,6}$")
DEFAULT_DB = Path("build/aerocie/federal_register.sqlite3")
DEFAULT_REVIEWS = Path("build/aerocie/reviewer_records")
DEFAULT_PACKET = Path("build/aerocie/reports/srp-source-review-packet.html")
DISPOSITIONS = ("hold_for_review", "source_reviewed_research_only")


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def snapshot(db: Path, document_number: str, *, fingerprint: str | None = None) -> dict[str, Any]:
    """Validate a pinned published metadata snapshot, or the latest local one."""
    if not DOC_RE.fullmatch(document_number):
        raise ValueError("Invalid Federal Register document number")
    if not db.is_file():
        raise FileNotFoundError(f"Missing collector database: {db}")
    if fingerprint is not None and (not isinstance(fingerprint, str) or
                                    not re.fullmatch(r"[0-9a-f]{64}", fingerprint)):
        raise ValueError("Invalid pinned SHA-256 fingerprint")
    clause = " AND fingerprint=?" if fingerprint is not None else ""
    params = (document_number, fingerprint) if fingerprint is not None else (document_number,)
    with closing(sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True)) as conn:
        row = conn.execute("""SELECT source, fingerprint, payload_json FROM document_snapshots
            WHERE source='published' AND document_number=?""" + clause + " ORDER BY id DESC LIMIT 1",
            params).fetchone()
    if row is None:
        raise ValueError("Published document absent from local database (or only in public inspection)")
    source, fingerprint, payload = row
    if not isinstance(payload, str) or not isinstance(fingerprint, str):
        raise ValueError("Snapshot payload and fingerprint must be strings")
    expected = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    if expected != fingerprint:
        raise ValueError("Stored collector fingerprint does not match the snapshot payload")
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError("Snapshot payload must be a JSON object")
    if data.get("document_number") != document_number or data.get("source") != "published":
        raise ValueError("Snapshot document metadata is inconsistent")
    return {"source": source, "fingerprint": fingerprint, "record": data}


def canonical(value: dict[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def record_review(db: Path, reviews_dir: Path, *, document_number: str, reviewer: str,
                  reviewer_role: str, notes: str, disposition: str = "hold_for_review",
                  federal_register_checked: bool = False, faa_drs_checked: bool = False,
                  supersession_checked: bool = False,
                  reviewed_at: str | None = None) -> dict[str, Any]:
    """Persist a self-attested manual receipt, not an authenticated signature."""
    reviewer, reviewer_role, notes = (x.strip() for x in (reviewer, reviewer_role, notes))
    if not reviewer or len(reviewer) > 120 or not reviewer_role or len(reviewer_role) > 160:
        raise ValueError("Provide a reviewer name and role (maximum 120/160 characters)")
    if len(notes) < 20 or len(notes) > 5000:
        raise ValueError("Review notes must be 20 to 5000 characters; record what was checked")
    if any(ord(ch) < 32 and ch not in "\n\t" for ch in reviewer+reviewer_role+notes):
        raise ValueError("Invalid control character in review fields")
    if disposition not in DISPOSITIONS:
        raise ValueError("Unsupported review disposition")
    if disposition == "source_reviewed_research_only" and not all((federal_register_checked,
                                                                      faa_drs_checked, supersession_checked)):
        raise ValueError("Source-reviewed designation requires all three explicit source checks")
    snap = snapshot(db, document_number)
    moment = reviewed_at or now_utc()
    parsed = dt.datetime.fromisoformat(moment)
    if parsed.tzinfo is None:
        raise ValueError("Review timestamp must have a timezone")
    receipt = {
        "schema_version": 1, "document_number": document_number,
        "source": "published", "collector_fingerprint": snap["fingerprint"],
        "review_id": uuid.uuid4().hex, "reviewed_at": moment,
        "reviewer": reviewer, "reviewer_role": reviewer_role,
        "notes": notes, "disposition": disposition,
        "checks": {"federal_register_checked": bool(federal_register_checked),
                   "faa_drs_checked": bool(faa_drs_checked),
                   "supersession_checked": bool(supersession_checked)},
        "limitations": "Manual self-attestation, not authenticated. Source verification only. No asset applicability, airworthiness or client-release approval.",
    }
    receipt["sha256"] = hashlib.sha256(canonical(receipt).encode("utf-8")).hexdigest()
    folder = reviews_dir / document_number
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{parsed.astimezone(dt.timezone.utc):%Y%m%dT%H%M%SZ}-{receipt['review_id']}.json"
    with path.open("x", encoding="utf-8") as fp:
        fp.write(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    return {"receipt_path": str(path), "document_number": document_number,
            "disposition": disposition, "collector_fingerprint": snap["fingerprint"],
            "status": "local_self_attested_receipt_not_identity_verified"}


def find_current_review(reviews_dir: Path, doc: str, fingerprint: str) -> dict[str, Any]:
    """Fail closed on stale or tampered receipts; never infer a positive review."""
    if not DOC_RE.fullmatch(doc):
        return {"state": "unreviewed"}
    folder = reviews_dir / doc
    if not folder.is_dir():
        return {"state": "unreviewed"}
    current = []
    invalid = False
    for path in sorted(folder.glob("*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            digest = raw.pop("sha256")
            if not isinstance(digest, str) or digest != hashlib.sha256(canonical(raw).encode("utf-8")).hexdigest():
                invalid = True
                continue
            if raw.get("document_number") != doc or raw.get("source") != "published":
                invalid = True
                continue
            if raw.get("collector_fingerprint") != fingerprint:
                continue
            if raw.get("disposition") not in DISPOSITIONS:
                invalid = True
                continue
            if raw.get("disposition") == "source_reviewed_research_only" and not all(raw.get("checks", {}).get(k) is True for k in (
                    "federal_register_checked", "faa_drs_checked", "supersession_checked")):
                invalid = True
                continue
            moment = dt.datetime.fromisoformat(raw["reviewed_at"])
            if moment.tzinfo is None:
                invalid = True
                continue
            current.append((moment, raw))
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            invalid = True
    # A corrupted receipt should never be treated as a clean reviewed record.
    if invalid:
        return {"state": "integrity_problem_requires_review"}
    if not current:
        return {"state": "stale_or_unreviewed"}
    raw = max(current, key=lambda x: x[0])[1]
    state = "source_reviewed_research_only" if raw["disposition"] == "source_reviewed_research_only" else "held_for_review"
    return {"state": state, "reviewer": raw["reviewer"], "reviewer_role": raw["reviewer_role"],
            "reviewed_at": raw["reviewed_at"], "notes": raw["notes"],
            "receipt_sha256": hashlib.sha256(canonical({k:v for k,v in raw.items()}).encode("utf-8")).hexdigest()}


def render_packet(items: list[dict[str, Any]], *, as_of: str, keyword: str | None = None) -> str:
    dt.date.fromisoformat(as_of)
    counts = {"source_reviewed_research_only": 0, "held_for_review": 0, "unreviewed": 0,
              "stale_or_unreviewed": 0, "integrity_problem_requires_review": 0}
    blocks = []
    for item in items:
        review = item["review"]
        state = review["state"]
        counts[state] = counts.get(state, 0) + 1
        source_links = " · ".join(filter(None, [safe_source_link(item.get("source_url"), "Federal Register"),
                                                    safe_source_link(item.get("official_pdf_url"), "Official PDF")])) or "Official source link unavailable"
        review_line = (f'<p><strong>Source reviewer:</strong> {esc(review.get("reviewer"))} '
                       f'({esc(review.get("reviewer_role"))}), {esc(review.get("reviewed_at"))}</p>'
                       f'<p><strong>Recorded notes:</strong> {esc(review.get("notes"))}</p>') if state in (
                           "held_for_review", "source_reviewed_research_only") else "<p>There is no current, integrity-checked review receipt for this metadata snapshot.</p>"
        blocks.append(f'''<section class="item"><div class="top"><h2>{esc(item.get("document_number"))} — {esc(item.get("title"))}</h2><span>{esc(item.get("publication_category"))}</span></div>
<p class="muted">Published {esc(item.get("publication_date"))} · Reported effective {esc(item.get("reported_effective_on"))} · {esc(item.get("triage_status"))}</p>
<p>Source links: {source_links}</p><p><strong>Manual source review status:</strong> {esc(state)}</p>{review_line}
<p class="warning">No asset-specific applicability determination. This record may have amendments, exclusions or incorporated material requiring further verification.</p></section>''')
    if not blocks:
        blocks.append('<p>No matching records. An empty report does not indicate regulatory clearance.</p>')
    count_reviewed = counts["source_reviewed_research_only"]
    status = "SOURCE-REVIEWED INTERNAL DRAFT" if count_reviewed == len(items) and items else "UNREVIEWED INTERNAL DRAFT"
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SRP AeroCIE Source Review Packet</title>
<style>:root{{--navy:#102b4b;--blue:#1769a0;--ink:#1a293b;--pale:#f2f6fa}}
*{{box-sizing:border-box}}body{{font-family:Arial,Helvetica,sans-serif;color:var(--ink);max-width:920px;margin:0 auto;padding:32px;line-height:1.52;font-size:13px}}
header{{border-bottom:5px solid var(--blue);padding-bottom:20px}}.brand{{font-weight:800;letter-spacing:1.4px;color:var(--navy);font-size:19px}}h1{{font-size:27px;color:var(--navy);line-height:1.2;margin:12px 0}}h2{{font-size:16px;line-height:1.4;color:var(--navy);margin:0}}
.caption{{text-transform:uppercase;color:var(--blue);letter-spacing:1.5px;font-weight:700;font-size:11px}}.muted,footer{{color:#465b70}}.notice{{border-left:5px solid var(--navy);background:var(--pale);padding:12px 15px;margin:16px 0}}
.metric{{border:1px solid #d4dde7;display:inline-block;padding:9px 14px;margin-right:8px}}.metric b{{font-size:19px;display:block;color:var(--navy)}}.item{{padding:18px 0;border-bottom:1px solid #d4dde7;break-inside:avoid}}
.top{{display:flex;justify-content:space-between;align-items:flex-start;gap:10px}}.top span{{font-size:11px;text-transform:uppercase;color:#486077;white-space:nowrap}}a{{color:#115f96}}.warning{{font-size:11px;color:#586a79}}footer{{border-top:2px solid #d4dde7;margin-top:24px;padding-top:10px;font-size:11px}}
@media print{{body{{max-width:none;padding:0}}@page{{size:letter;margin:.65in}}.item{{break-inside:avoid}}a{{color:#202938}}}}
</style></head><body><header><div class="brand">STRATEGICRISK PARTNERS</div><div class="caption">AeroCIE · Aviation regulatory intelligence</div>
<h1>Source Verification &amp; Research Packet</h1><p class="muted">As-of (UTC): {esc(as_of)} · Selection: {esc(keyword or "all locally collected FAA publications")}</p></header>
<div class="notice"><strong>{status} — NOT AUTOMATICALLY APPROVED FOR CLIENT DISTRIBUTION.</strong><p>Manual source checks are self-attested and not authenticated. This is regulatory research, not legal advice or an FAA/airworthiness certification. Qualified review, supersession checks, affected asset and installed-part/serial analysis, and separate commercial approval remain necessary. A published rule does not automatically apply to an operator; a proposal is not an adopted obligation. Completeness of regulatory coverage is not guaranteed.</p></div>
<div class="metric"><b>{len(items)}</b>records</div><div class="metric"><b>{count_reviewed}</b>source-reviewed</div><div class="metric"><b>{len(items)-count_reviewed}</b>not source-verified</div>
<h2 style="margin-top:22px">Source-linked findings</h2>{''.join(blocks)}
<footer>StrategicRisk Partners LLC · AeroCIE local research prototype. Research sources originate in the Federal Register; no government affiliation. This packet is a review artifact only, not a determination of aircraft safety, AD compliance, or insurance coverage. Release authorization is outside this application.</footer>
</body></html>'''


def create_packet(db: Path, reviews_dir: Path, *, out: Path, keyword: str | None = None,
                  limit: int = 100, as_of: str | None = None) -> dict[str, Any]:
    if limit < 1 or limit > 1000:
        raise ValueError("--limit must be 1..1000")
    day = as_of or dt.datetime.now(dt.timezone.utc).date().isoformat()
    dt.date.fromisoformat(day)
    records = latest_documents(db, keyword=keyword, limit=limit, as_of=day)
    for item in records:
        if item.get("source") != "published":
            item["review"] = {"state": "unreviewed"}
            continue
        try:
            snap = snapshot(db, str(item.get("document_number")))
            item["review"] = find_current_review(reviews_dir, str(item["document_number"]), snap["fingerprint"])
        except (ValueError, FileNotFoundError, sqlite3.Error):
            item["review"] = {"state": "integrity_problem_requires_review"}
    content = render_packet(records, as_of=day, keyword=keyword)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8")
    n_verified = sum(i["review"]["state"] == "source_reviewed_research_only" for i in records)
    return {"as_of": day, "records": len(records), "source_reviewed": n_verified,
            "unverified_or_held": len(records)-n_verified, "report_path": str(out),
            "status": "internal_draft_separate_client_release_approval_required"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AeroCIE-007 local self-attested source review and internal research packet")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--reviews-dir", type=Path, default=DEFAULT_REVIEWS)
    sub = parser.add_subparsers(dest="action", required=True)
    record = sub.add_parser("record", help="Record a qualified human source-check receipt")
    record.add_argument("--document-number", required=True)
    record.add_argument("--reviewer", required=True)
    record.add_argument("--reviewer-role", required=True)
    record.add_argument("--notes", required=True)
    record.add_argument("--disposition", choices=DISPOSITIONS, default="hold_for_review")
    record.add_argument("--federal-register-checked", action="store_true")
    record.add_argument("--faa-drs-checked", action="store_true")
    record.add_argument("--supersession-checked", action="store_true")
    packet = sub.add_parser("packet", help="Generate an SRP-branded internal, print-ready packet")
    packet.add_argument("--keyword")
    packet.add_argument("--limit", type=int, default=100)
    packet.add_argument("--as-of")
    packet.add_argument("--out", type=Path, default=DEFAULT_PACKET)
    args = parser.parse_args(argv)
    try:
        if args.action == "record":
            outcome = record_review(args.db, args.reviews_dir, document_number=args.document_number,
                                    reviewer=args.reviewer, reviewer_role=args.reviewer_role,
                                    notes=args.notes, disposition=args.disposition,
                                    federal_register_checked=args.federal_register_checked,
                                    faa_drs_checked=args.faa_drs_checked,
                                    supersession_checked=args.supersession_checked)
        else:
            outcome = create_packet(args.db, args.reviews_dir, out=args.out,
                                    keyword=args.keyword, limit=args.limit, as_of=args.as_of)
        print(json.dumps(outcome, indent=2))
        return 0
    except (ValueError, OSError, sqlite3.Error, json.JSONDecodeError) as exc:
        print(f"AeroCIE source review error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
