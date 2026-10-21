"""Review-required, print-ready AeroCIE research packet; no legal determinations.

Reads the existing snapshot database without modifying it. Deliberately produces
HTML for browser Print -> Save PDF, without paid dependencies or external assets.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import sys
import urllib.parse
from pathlib import Path
from typing import Any

from .review_queue import latest_documents

SAFE_DOC_RE = re.compile(r"^\d{4}-\d{4,6}$")
ALLOWED_SOURCES = {
    "www.federalregister.gov",
    "federalregister.gov",
    "www.govinfo.gov",
    "govinfo.gov",
}


def safe_source_link(value: object, label: str) -> str:
    if not isinstance(value, str):
        return ""
    try:
        parsed = urllib.parse.urlsplit(value)
    except ValueError:
        return ""
    if (parsed.scheme != "https" or parsed.hostname not in ALLOWED_SOURCES
            or parsed.username is not None or parsed.password is not None
            or parsed.port not in (None, 443)):
        return ""
    # HTTP URL could contain controls or a hostile navigation attempt.
    if any(ord(c) < 32 or ord(c) == 127 for c in value):
        return ""
    return f'<a rel="noopener noreferrer" href="{html.escape(value, quote=True)}">{html.escape(label)}</a>'


def esc(value: object) -> str:
    return html.escape(str(value) if value is not None else "Not reported", quote=True)


def _as_date(value: str | None) -> str:
    day = value or dt.datetime.now(dt.timezone.utc).date().isoformat()
    dt.date.fromisoformat(day)
    return day


def render_report(items: list[dict[str, Any]], *, as_of: str,
                  report_title: str = "Aviation Regulatory Intelligence | Review Draft",
                  scope: str = "Selected locally archived FAA Federal Register publications",
                  run_context: str = "Read-only snapshot review") -> str:
    """Render an unambiguous review DRAFT; never mark evidence as compliant."""
    _as_date(as_of)
    if len(items) > 1000:
        raise ValueError("Review packet maximum is 1000 records")
    counts: dict[str, int] = {}
    for item in items:
        category = str(item.get("publication_category") or "unclassified")
        counts[category] = counts.get(category, 0) + 1
    rows = []
    for item in items:
        document_number = item.get("document_number") or "Unknown"
        links = " · ".join(filter(None, [
            safe_source_link(item.get("source_url"), "Federal Register"),
            safe_source_link(item.get("official_pdf_url"), "Official PDF"),
        ])) or "Source link unavailable—manual verification required"
        if isinstance(item.get("docket_ids"), list):
            docket = "; ".join(str(x) for x in item["docket_ids"][:20])
        else:
            docket = "Not reported"
        event = item.get("monitor_event")
        event_info = f'<p class="meta">Local collector event: {esc(event)}</p>' if event else ""
        rows.append(f'''<article class="finding">
          <div class="row"><h3>{esc(document_number)} — {esc(item.get("title"))}</h3><span class="pill">{esc(item.get("publication_category"))}</span></div>
          <p class="meta">Published: {esc(item.get("publication_date"))} · Reported effective: {esc(item.get("reported_effective_on"))}
          · Status: {esc(item.get("triage_status"))}</p>
          {event_info}
          <p><strong>Agency action:</strong> {esc(item.get("agency_action"))}</p>
          <p><strong>Dates statement:</strong> {esc(item.get("reported_dates_text"))}</p>
          <p><strong>Docket identifiers:</strong> {esc(docket)}</p>
          <p><strong>Sources:</strong> {links}</p>
          <div class="review">REVIEW REQUIRED · No asset applicability or legal-compliance determination
          <div>Reviewer: ____________________ &nbsp; Verification date: ________________</div></div>
        </article>''')
    if not rows:
        rows.append('<p>No records matched this report scope. This is not a regulatory clearance.</p>')
    total = len(items)
    # No external styles, scripts, or company assets; suitable for offline use.
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(report_title)}</title>
<style>
:root{{--navy:#102c4d;--blue:#176ba0;--ink:#202938;--muted:#526479;--border:#cfdae5}}
*{{box-sizing:border-box}}body{{max-width:920px;margin:0 auto;padding:34px;font:14px/1.55 Arial,Helvetica,sans-serif;color:var(--ink)}}
header{{border-bottom:4px solid var(--blue);padding-bottom:20px}}h1{{font-size:25px;color:var(--navy);margin:4px 0}}h2{{font-size:19px;color:var(--navy)}}h3{{font-size:15px;color:var(--navy);margin:0;line-height:1.4}}p{{margin:8px 0}}
.eyebrow{{text-transform:uppercase;letter-spacing:1.2px;font-weight:bold;color:var(--blue);font-size:11px}}.disclaimer{{border-left:4px solid var(--navy);background:#f1f5f9;padding:13px;margin:17px 0}}.meta{{color:var(--muted)}}
.metrics{{display:flex;gap:18px;flex-wrap:wrap;margin:20px 0}}.metric{{min-width:140px;border:1px solid var(--border);padding:12px}}.metric b{{font-size:22px;color:var(--navy);display:block}}
.finding{{border-top:1px solid var(--border);padding:18px 0;break-inside:avoid-page}}.row{{display:flex;align-items:flex-start;justify-content:space-between;gap:12px}}.pill{{border:1px solid var(--border);border-radius:12px;padding:2px 9px;white-space:nowrap;font-size:11px}}
a{{color:#135b91}}.review{{background:#f7f9fc;border:1px solid var(--border);font-size:12px;font-weight:bold;padding:10px;margin-top:12px}}.review div{{font-weight:normal;margin-top:8px}}
footer{{font-size:11px;color:var(--muted);padding-top:18px;border-top:1px solid var(--border)}}
@media print{{body{{padding:0;max-width:none}}a{{color:#202938;text-decoration:underline}}.finding{{break-inside:avoid}}@page{{size:letter;margin:0.65in}}}}
</style></head><body>
<header><div class="eyebrow">StrategicRisk Partners · AeroCIE</div>
<h1>{esc(report_title)}</h1><p>{esc(scope)}</p><p class="meta">As-of date (UTC): {esc(as_of)} · {esc(run_context)}</p></header>
<div class="disclaimer"><strong>DRAFT — HUMAN REVIEW REQUIRED. NOT FOR CLIENT RELEASE WITHOUT QUALIFIED REVIEW.</strong>
This report is preliminary regulatory research. A new local record is not a newly effective legal obligation. Published, proposed and public-inspection items have distinct statuses. Reported dates, official sources, supersession, incorporated material, applicability, model/part/serial ranges and compliance requirements must be independently checked. No airworthiness or compliance certification is provided.</div>
<div class="metrics"><div class="metric"><b>{total}</b>records in packet</div>
<div class="metric"><b>{counts.get("rule",0)}</b>published rules</div>
<div class="metric"><b>{counts.get("proposed_rule",0)}</b>proposed rules</div>
<div class="metric"><b>{counts.get("notice",0)}</b>notices</div></div>
<h2>Source-linked review items</h2>{''.join(rows)}
<footer>StrategicRisk Partners LLC · AeroCIE local research prototype · Public-source metadata only; not a government affiliation or FAA-certified service. Evidence as of {esc(as_of)}. No customer-specific applicability has been verified.</footer>
</body></html>'''


def create_report(db: Path, *, out: Path, keyword: str | None = None,
                  limit: int = 100, as_of: str | None = None) -> dict[str, Any]:
    if limit < 1 or limit > 1000:
        raise ValueError("--limit must be 1–1000")
    day = _as_date(as_of)
    records = latest_documents(db, keyword=keyword, limit=limit, as_of=day)
    output = render_report(records, as_of=day,
                           scope=(f"FAA Federal Register publications matching keyword: {keyword}" if keyword else "FAA Federal Register publications in local research database"))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(output, encoding="utf-8")
    return {"as_of": day, "records": len(records), "report_path": str(out),
            "status": "draft_human_review_required"}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="AeroCIE local, source-linked review DRAFT (HTML / browser Save as PDF)")
    p.add_argument("--db", type=Path, default=Path("build/aerocie/federal_register.sqlite3"))
    p.add_argument("--out", type=Path, default=Path("build/aerocie/reports/review-draft.html"))
    p.add_argument("--keyword", default=None)
    p.add_argument("--limit", type=int, default=100)
    p.add_argument("--as-of", default=None)
    args = p.parse_args(argv)
    try:
        print(json.dumps(create_report(args.db, out=args.out, keyword=args.keyword,
                                       limit=args.limit, as_of=args.as_of), indent=2))
        return 0
    except (ValueError, OSError, FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"AeroCIE report error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
