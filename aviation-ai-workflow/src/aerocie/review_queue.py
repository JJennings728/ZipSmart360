"""Read-only AeroCIE review queue from existing Federal Register SQLite snapshots.

Classifies publication *type*, NOT aircraft-level applicability or legal compliance.
Does not contact any API, alter the collector, or modify the database.
"""
from __future__ import annotations
from contextlib import closing
import argparse
import csv
import datetime as dt
import io
import json
import sqlite3
import sys
from pathlib import Path


def _kind(value: str | None) -> str:
    norm = (value or "").strip().upper().replace("_", " ").replace("-", " ")
    if norm in ("PRORULE", "PROPOSED RULE", "PROPOSED RULES"):
        return "proposed_rule"
    if norm in ("RULE", "FINAL RULE", "RULES AND REGULATIONS"):
        return "rule"
    if norm in ("NOTICE", "NOTICES"):
        return "notice"
    return "unclassified"


def _is_future(date_string: str | None, as_of: str) -> bool | None:
    if not date_string:
        return None
    try:
        return dt.date.fromisoformat(date_string) > dt.date.fromisoformat(as_of)
    except (ValueError, TypeError):
        return None


def classify(doc: dict, *, as_of: str) -> dict:
    """Conservative initial triage. Final status requires source and FAA DRS review."""
    kind = _kind(doc.get("document_type"))
    source = doc.get("source")
    eff = doc.get("effective_on")
    if source == "public_inspection":
        status = "public_inspection_not_published"
    elif kind == "proposed_rule":
        status = "proposal_not_an_adopted_final_rule"
    elif kind == "rule":
        future = _is_future(eff, as_of)
        status = ("published_rule_future_reported_effective_date" if future is True
                  else "published_rule_effective_date_requires_review")
    elif kind == "notice":
        status = "notice_review_relevance"
    else:
        status = "unclassified_manual_review"
    return {
        "document_number": doc.get("document_number"),
        "title": doc.get("title"),
        "source": source,
        "document_type": doc.get("document_type"),
        "publication_category": kind,
        "triage_status": status,
        "publication_date": doc.get("publication_date"),
        "reported_effective_on": eff,
        "reported_dates_text": doc.get("dates_text"),
        "agency_action": doc.get("action"),
        "source_url": doc.get("html_url"),
        "official_pdf_url": doc.get("pdf_url"),
        "docket_ids": doc.get("docket_ids"),
        "review_required": True,
        "asset_applicability_verified": False,
    }


def latest_documents(db_path: Path, *, keyword: str | None = None, limit: int = 100,
                     as_of: str | None = None) -> list[dict]:
    if not db_path.is_file():
        raise FileNotFoundError(f"No AeroCIE database found at: {db_path}")
    if limit < 1 or limit > 1000:
        raise ValueError("--limit must be between 1 and 1000")
    on_date = as_of or dt.datetime.now(dt.timezone.utc).date().isoformat()
    dt.date.fromisoformat(on_date)
    # Open SQLite as read-only; URI is formed from a resolved local path.
    with closing(sqlite3.connect(f"file:{db_path.resolve().as_posix()}?mode=ro", uri=True)) as conn:
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='document_snapshots'").fetchall()
        if not tables:
            raise ValueError("This database does not contain AeroCIE document_snapshots")
        rows = conn.execute("""
            SELECT d.payload_json FROM document_snapshots AS d
            JOIN (SELECT source, document_number, MAX(id) AS most_recent
                  FROM document_snapshots GROUP BY source, document_number) AS latest
              ON d.id = latest.most_recent
            ORDER BY d.id DESC
        """).fetchall()
    results = []
    for (encoded,) in rows:
        doc = json.loads(encoded)
        text = " ".join(str(doc.get(field) or "") for field in ("title", "abstract", "action", "document_number"))
        if keyword and keyword.casefold() not in text.casefold():
            continue
        results.append(classify(doc, as_of=on_date))
        if len(results) >= limit:
            break
    return results


def write_csv(items: list[dict]) -> str:
    out = io.StringIO()
    fields = list(classify({}, as_of="2026-10-20").keys())
    writer = csv.DictWriter(out, fieldnames=fields)
    writer.writeheader()
    for item in items:
        writer.writerow({k:json.dumps(v) if isinstance(v,(list,dict)) else v for k,v in item.items()})
    return out.getvalue()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="AeroCIE reviewed-documents queue (not a compliance determination)")
    p.add_argument("--db", type=Path, default=Path("build/aerocie/federal_register.sqlite3"))
    p.add_argument("--keyword", default=None, help="Filter by keyword in title, abstract, action or document number")
    p.add_argument("--limit", type=int, default=100)
    p.add_argument("--as-of", default=None, help="UTC YYYY-MM-DD; for a reproducible demonstration")
    p.add_argument("--format", choices=("json", "csv"), default="json")
    p.add_argument("--out", type=Path, default=None, help="Optional export destination")
    args = p.parse_args(argv)
    try:
        items = latest_documents(args.db, keyword=args.keyword, limit=args.limit, as_of=args.as_of)
        if args.format == "csv":
            output = write_csv(items)
        else:
            output = json.dumps({
                "records_reviewed": len(items),
                "review_required": len(items),
                "records": items,
                "limitations": "Document type is a preliminary triage, not a verified current AD, compliance status, or asset-specific applicability. Verify official FAA source and effective dates."
            }, indent=2, ensure_ascii=False)
        if args.out is not None:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(output, encoding="utf-8")
            print(f"Exported {len(items)} review records to {args.out}")
        else:
            print(output)
        return 0
    except (ValueError, FileNotFoundError, sqlite3.Error, json.JSONDecodeError) as exc:
        print(f"AeroCIE review error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
