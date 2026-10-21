"""Repeatable AeroCIE FAA monitoring using an existing local SQLite baseline.

Local-only, public API, no secrets. This is not a continuous service: execute
regularly using Windows Task Scheduler or another user-controlled scheduler.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import datetime as dt
import json
import sqlite3
import sys
import urllib.error
from pathlib import Path
from typing import Any, Callable

from . import fr_collector as fr
from .report import render_report
from .review_queue import classify


def run_monitor(*, db: Path, since: str, limit: int = 300,
                include_inspection: bool = False, inspection_limit: int = 100,
                agency: str = fr.DEFAULT_AGENCY,
                get_json: Callable[..., Any] = fr.fetch_json) -> dict[str, Any]:
    dt.date.fromisoformat(since)
    if not 1 <= limit <= 500 or not 1 <= inspection_limit <= 500:
        raise ValueError("Limits must be 1–500")
    # Fetch all sources BEFORE opening/updating SQLite. A failed request must not
    # claim successful monitoring or partially apply a multi-source scan.
    published = fr.search_published(since=since, limit=limit, agency=agency,
                                    get_json=get_json)
    inspection = (fr.search_inspection(limit=inspection_limit, agency=agency,
                                      get_json=get_json)
                  if include_inspection else [])
    warnings: list[str] = []
    if len(published) >= limit:
        warnings.append("Published search reached its document cap; scan completeness is UNKNOWN. Increase --limit or reduce the lookback window.")
    if include_inspection and len(inspection) >= inspection_limit:
        warnings.append("Public-inspection query reached its cap; scan completeness is UNKNOWN.")
    db.parent.mkdir(parents=True, exist_ok=True)
    initial = False
    all_events: list[dict[str, Any]] = []
    day = dt.datetime.now(dt.timezone.utc).date().isoformat()
    # Use explicit closing: sqlite3's context manager alone does not close on Windows.
    with closing(sqlite3.connect(db, timeout=15)) as conn:
        fr.initialize(conn)
        previous_count = conn.execute("SELECT COUNT(*) FROM document_snapshots").fetchone()[0]
        initial = previous_count == 0
        for source, rows in (("published", published), ("public_inspection", inspection)):
            for row in rows:
                event = fr.ingest(conn, row, source=source)
                if event["event"] == "unchanged":
                    continue
                doc = fr.canonical_record(row, source=source)
                enriched = classify(doc, as_of=day)
                enriched["monitor_event"] = event["event"]
                all_events.append(enriched)
    new_count = sum(r["monitor_event"] == "new" for r in all_events)
    changed_count = sum(r["monitor_event"] == "metadata_changed" for r in all_events)
    return {
        "run_at": fr.utc_now(), "since": since, "agency": agency,
        "sources": ["published"] + (["public_inspection"] if include_inspection else []),
        "published_checked": len(published), "inspection_checked": len(inspection),
        "new_to_database": new_count, "metadata_changed": changed_count,
        "unchanged": len(published) + len(inspection) - len(all_events),
        "baseline_created": initial,
        "review_items": all_events,
        "warnings": warnings,
        "scan_complete": not bool(warnings),
        "notifications_sent": False,
        "limitations": "New means new to the local database, not new law. Metadata changes may be editorial. No full-text amendments, asset compliance or legal status determination; no outbound alerts.",
    }


def save_run(result: dict[str, Any], *, directory: Path) -> tuple[Path, Path]:
    """Preserve every run separately, without rewriting previous evidence."""
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = result["run_at"].replace(":", "-").replace("+", "_")
    stem = f"aerocie-monitor-{timestamp}"
    json_path = directory / f"{stem}.json"
    html_path = directory / f"{stem}.html"
    # Fail rather than accidentally overwrite the evidence for a prior run.
    index = 1
    while json_path.exists() or html_path.exists():
        json_path = directory / f"{stem}-{index}.json"
        html_path = directory / f"{stem}-{index}.html"
        index += 1
    html_output = render_report(result["review_items"], as_of=result["run_at"][:10],
                                report_title="FAA Publication Monitoring | Review Draft",
                                scope=f"FAA publications retrieved since {result['since']} (UTC); changed/new local records only",
                                run_context=("First local baseline scan" if result["baseline_created"] else "Repeat local monitoring scan"))
    # A cap warning must remain visible in the saved report as well as JSON.
    if result["warnings"]:
        warnings = " ".join(result["warnings"])
        import html
        html_output = html_output.replace("<h2>Source-linked review items</h2>",
            '<div class="disclaimer"><strong>INCOMPLETE SEARCH: ' + html.escape(warnings) +
            '</strong></div><h2>Source-linked review items</h2>')
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    html_path.write_text(html_output, encoding="utf-8")
    return json_path, html_path


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="AeroCIE repeat FAA publication checks and save review artifacts")
    p.add_argument("--db", type=Path, default=Path("build/aerocie/federal_register.sqlite3"))
    p.add_argument("--lookback-days", type=int, default=7)
    p.add_argument("--since", default=None, help="Override rolling UTC start date (YYYY-MM-DD)")
    p.add_argument("--limit", type=int, default=300)
    p.add_argument("--include-inspection", action="store_true", help="Also check preliminary public-inspection records")
    p.add_argument("--inspection-limit", type=int, default=100)
    p.add_argument("--report-dir", type=Path, default=Path("build/aerocie/reports"))
    args = p.parse_args(argv)
    try:
        if args.lookback_days < 1 or args.lookback_days > 60:
            raise ValueError("--lookback-days must be between 1 and 60")
        since = args.since or (dt.datetime.now(dt.timezone.utc).date() -
                               dt.timedelta(days=args.lookback_days)).isoformat()
        result = run_monitor(db=args.db, since=since, limit=args.limit,
                             include_inspection=args.include_inspection,
                             inspection_limit=args.inspection_limit)
        json_path, html_path = save_run(result, directory=args.report_dir)
        print(json.dumps({k: v for k, v in result.items() if k != "review_items"} |
                         {"review_item_count": len(result["review_items"]),
                          "run_json": str(json_path), "review_html": str(html_path)},
                         indent=2, ensure_ascii=False))
        return 2 if result["warnings"] else 0
    except (ValueError, FileNotFoundError, OSError, sqlite3.Error, urllib.error.HTTPError,
            urllib.error.URLError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"AeroCIE monitor error (run NOT certified complete): {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
