"""FederalRegister.gov ingestion for AeroCIE (public prototype, not legal advice).

Uses only the Python standard library; no API keys or customer information.

Important limitations:
- Records published-document metadata, not the authoritative full legal text.
- Changes to the metadata are NOT automatically regulatory amendments.
- Public-inspection documents are staged separately from published documents.
- Effective dates may be unavailable or different from publication dates.
- Verify findings against the official Federal Register edition and FAA DRS.
"""

from __future__ import annotations

import argparse
import datetime as dt
import difflib
import hashlib
import json
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable

BASE_URL = "https://www.federalregister.gov/api/v1/"
DEFAULT_AGENCY = "federal-aviation-administration"
DOC_FIELDS = (
    "document_number", "title", "type", "publication_date", "effective_on",
    "abstract", "action", "dates", "agencies", "cfr_references",
    "citation", "docket_ids", "html_url", "pdf_url", "raw_text_url",
    "json_url", "corrections", "correction_of",
)
DOC_ID_RE = re.compile(r"^\d{4}-\d{4,6}$")
SOURCE_TYPES = ("published", "public_inspection")
MAX_RESPONSE_BYTES = 5_000_000


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _encode_params(params: list[tuple[str, str]] | None) -> str:
    return urllib.parse.urlencode(params or [])


def fetch_json(
    path: str,
    params: list[tuple[str, str]] | None = None,
    *,
    retries: int = 2,
    timeout: int = 20,
) -> Any:
    """Fetch only a relative path at the Federal Register API origin."""
    if not path or path.startswith("/") or ":" in path or ".." in path or "?" in path:
        raise ValueError("API paths must be safe relative paths without query strings")
    uri = BASE_URL + path
    query = _encode_params(params)
    if query:
        uri += "?" + query
    request = urllib.request.Request(
        uri,
        headers={"Accept": "application/json", "User-Agent": "SRP-AeroCIE-Prototype/0.1 (regulatory research)"},
    )
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
                if len(raw) > MAX_RESPONSE_BYTES:
                    raise ValueError("API response larger than supported limit")
                return json.loads(raw.decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == retries:
                raise
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt == retries:
                raise RuntimeError(f"Federal Register API temporarily unreachable: {exc}") from exc
        time.sleep(min(2**attempt, 4))
    raise RuntimeError("Unreachable retry state")


def published_query(
    *, since: str, agency: str = DEFAULT_AGENCY, cfr_part: int | None = None,
    term: str | None = None, page: int = 1, per_page: int = 20,
) -> list[tuple[str, str]]:
    dt.date.fromisoformat(since)
    if cfr_part is not None and cfr_part <= 0:
        raise ValueError("CFR part must be positive")
    if not 1 <= per_page <= 100:
        raise ValueError("per_page must be 1–100")
    if page < 1:
        raise ValueError("page must be positive")
    query = [
        ("conditions[agencies][]", agency),
        ("conditions[publication_date][gte]", since),
        ("order", "newest"), ("page", str(page)), ("per_page", str(per_page)),
    ]
    # CFR Title 14 includes civil aviation and commercial space regulations.
    if cfr_part is not None:
        query.extend((("conditions[cfr][title]", "14"), ("conditions[cfr][part]", str(cfr_part))))
    if term:
        query.append(("conditions[term]", term))
    query.extend(("fields[]", f) for f in DOC_FIELDS)
    return query


def unpack_results(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        records = payload
    elif isinstance(payload, dict):
        records = payload.get("results")
        if records is None:
            # Some API shapes wrap current public-inspection documents.
            records = payload.get("documents", [])
    else:
        raise ValueError("Unexpected API response structure")
    if not isinstance(records, list) or any(not isinstance(x, dict) for x in records):
        raise ValueError("API search results must be a list of objects")
    return records


def canonical_record(row: dict[str, Any], *, source: str) -> dict[str, Any]:
    if source not in SOURCE_TYPES:
        raise ValueError("Unsupported source category")
    doc_number = row.get("document_number")
    if not isinstance(doc_number, str) or not DOC_ID_RE.fullmatch(doc_number):
        raise ValueError(f"Document number missing or invalid: {doc_number!r}")
    return {
        "source": source,
        "document_number": doc_number,
        "title": row.get("title"),
        "document_type": row.get("type"),
        "publication_date": row.get("publication_date"),
        # Never substitute publication_date for effective_on.
        "effective_on": row.get("effective_on"),
        "filed_at": row.get("filed_at"),
        "filing_type": row.get("filing_type"),
        "abstract": row.get("abstract"),
        "action": row.get("action"),
        "dates_text": row.get("dates"),
        "agencies": row.get("agencies"),
        "cfr_references": row.get("cfr_references"),
        "citation": row.get("citation"),
        "docket_ids": row.get("docket_ids"),
        "html_url": row.get("html_url"),
        "pdf_url": row.get("pdf_url"),
        "raw_text_url": row.get("raw_text_url"),
        "json_url": row.get("json_url"),
        "corrections": row.get("corrections"),
        "correction_of": row.get("correction_of"),
        "status": "public_inspection_unpublished" if source == "public_inspection" else "published_verify_effective_date",
        "verified_asset_applicability": False,
    }


def fingerprint(record: dict[str, Any]) -> tuple[str, str]:
    raw = json.dumps(record, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest(), raw


def initialize(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS document_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            document_number TEXT NOT NULL,
            fingerprint TEXT NOT NULL,
            fetched_at TEXT NOT NULL,
            payload_json TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS snapshots_lookup
          ON document_snapshots(source, document_number, id DESC);
        CREATE TABLE IF NOT EXISTS change_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            document_number TEXT NOT NULL,
            previous_fingerprint TEXT,
            current_fingerprint TEXT NOT NULL,
            observed_at TEXT NOT NULL,
            event_type TEXT NOT NULL,
            diff_excerpt TEXT NOT NULL
        );
    """)
    conn.commit()


def ingest(conn: sqlite3.Connection, row: dict[str, Any], *, source: str,
           observed_at: str | None = None) -> dict[str, Any]:
    record = canonical_record(row, source=source)
    digest, encoded = fingerprint(record)
    prior = conn.execute("""
        SELECT fingerprint, payload_json FROM document_snapshots
        WHERE source=? AND document_number=? ORDER BY id DESC LIMIT 1
    """, (source, record["document_number"])).fetchone()
    if prior and prior[0] == digest:
        return {"event": "unchanged", "source": source, "document_number": record["document_number"]}
    event = "new" if prior is None else "metadata_changed"
    excerpt = ""
    if prior is not None:
        previous = json.dumps(json.loads(prior[1]), indent=2, sort_keys=True).splitlines()
        current = json.dumps(json.loads(encoded), indent=2, sort_keys=True).splitlines()
        excerpt = "\n".join(list(difflib.unified_diff(previous, current, lineterm=""))[:120])[:10000]
    ts = observed_at or utc_now()
    with conn:
        conn.execute("""
            INSERT INTO document_snapshots
              (source, document_number, fingerprint, fetched_at, payload_json)
            VALUES (?, ?, ?, ?, ?)
        """, (source, record["document_number"], digest, ts, encoded))
        conn.execute("""
            INSERT INTO change_events
              (source, document_number, previous_fingerprint, current_fingerprint,
               observed_at, event_type, diff_excerpt)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (source, record["document_number"], prior[0] if prior else None,
              digest, ts, event, excerpt))
    return {"event": event, "source": source, "document_number": record["document_number"],
            "title": record["title"], "url": record["html_url"],
            "publication_date": record["publication_date"], "effective_on": record["effective_on"],
            "status": record["status"]}


def search_published(
    *, since: str, limit: int, agency: str = DEFAULT_AGENCY,
    cfr_part: int | None = None, term: str | None = None,
    get_json: Callable[..., Any] = fetch_json,
) -> list[dict[str, Any]]:
    if not 1 <= limit <= 500:
        raise ValueError("Limit must be between 1 and 500")
    documents: list[dict[str, Any]] = []
    page = 1
    while len(documents) < limit:
        remaining = limit - len(documents)
        per_page = min(100, remaining)
        payload = get_json("documents.json", published_query(
            since=since, agency=agency, cfr_part=cfr_part, term=term,
            page=page, per_page=per_page))
        rows = unpack_results(payload)
        documents.extend(rows[:remaining])
        if len(rows) < per_page:
            break
        # Avoid traversing beyond Federal Register's first 2,000 results.
        if page * per_page >= 2000:
            break
        page += 1
    return documents


def search_inspection(
    *, limit: int, agency: str = DEFAULT_AGENCY,
    get_json: Callable[..., Any] = fetch_json,
) -> list[dict[str, Any]]:
    if not 1 <= limit <= 500:
        raise ValueError("Limit must be between 1 and 500")
    # Query by agency rather than retrieving all agencies' current filings.
    payload = get_json("public-inspection-documents.json", [
        ("conditions[agencies][]", agency), ("per_page", str(limit)),
        ("page", "1"),
    ])
    return unpack_results(payload)[:limit]


def run(args: argparse.Namespace, *, get_json: Callable[..., Any] = fetch_json) -> dict[str, Any]:
    if args.mode == "agencies":
        records = get_json("agencies")
        if not isinstance(records, list):
            raise ValueError("Expected a list of agencies")
        matches = [r for r in records if isinstance(r, dict) and
                   ("aviation" in str(r.get("name", "")).lower() or
                    "space" in str(r.get("name", "")).lower())]
        return {"mode": "agencies", "matches": matches}
    if args.mode == "document":
        if not args.document_number or not DOC_ID_RE.fullmatch(args.document_number):
            raise ValueError("Specify a valid --document-number such as 2024-06419")
        rows = [get_json(f"documents/{args.document_number}.json")]
        source = "published"
    elif args.mode == "inspection":
        rows = search_inspection(limit=args.limit, agency=args.agency, get_json=get_json)
        source = "public_inspection"
    else:
        rows = search_published(
            since=args.since, limit=args.limit, agency=args.agency,
            cfr_part=args.cfr_part, term=args.term, get_json=get_json)
        source = "published"
    args.db.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(args.db) as conn:
        initialize(conn)
        events: list[dict[str, Any]] = []
        for row in rows:
            events.append(ingest(conn, row, source=source))
    return {
        "run_at": utc_now(), "mode": args.mode, "source": source,
        "records_checked": len(events),
        "new": sum(e["event"] == "new" for e in events),
        "metadata_changed": sum(e["event"] == "metadata_changed" for e in events),
        "unchanged": sum(e["event"] == "unchanged" for e in events),
        "events": events,
        "limitations": "Metadata change detection only. No verified current AD applicability, full-text diff, or effective-date determination.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AeroCIE Federal Register collector (research prototype)")
    parser.add_argument("--mode", choices=("published", "inspection", "document", "agencies"), default="published")
    parser.add_argument("--since", default=(dt.datetime.now(dt.timezone.utc).date() - dt.timedelta(days=30)).isoformat())
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--agency", default=DEFAULT_AGENCY)
    parser.add_argument("--cfr-part", type=int, default=None, help="Optional 14 CFR part filter (e.g. 450 for launch/reentry)")
    parser.add_argument("--term", default=None, help="Optional full-text search term")
    parser.add_argument("--document-number", default=None)
    parser.add_argument("--db", type=Path, default=Path("build/aerocie/federal_register.sqlite3"))
    args = parser.parse_args(argv)
    try:
        result = run(args)
    except (ValueError, urllib.error.HTTPError, RuntimeError, json.JSONDecodeError, sqlite3.Error) as exc:
        print(f"AeroCIE collector error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
