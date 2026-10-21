"""AeroCIE-005: offline, loopback-only Federal Register evidence review dashboard.

Read-only presentation of collected metadata and SHA256-verified cached evidence.
NO live regulatory fetch, no compliance/airworthiness determination, no customer portal.
Python standard library only. Explicit sqlite3.close to support Windows 3.14.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import sqlite3
import sys
from urllib.parse import parse_qs, urlsplit
import webbrowser

from .asset_screen import latest_snapshots, screen_documents, validate_model
from .review_queue import classify
from .full_text_review import screen_full_text

DOCUMENT_NUMBER_RE = re.compile(r"\d{4}-\d{4,6}\Z")
SHA256_RE = re.compile(r"[a-f0-9]{64}\Z")
MAX_VIEW_ROWS = 100

CSS = """
:root{color-scheme:light;font-family:Arial,Helvetica,sans-serif;background:#f3f6fa;color:#172b44}
*{box-sizing:border-box}body{margin:0}a{color:#135ab3}a:hover{text-decoration:underline}
header{background:#0a2646;color:#fff;padding:24px max(24px,calc((100vw - 1120px)/2));border-bottom:5px solid #266fc0}
header p{margin:6px 0 0;color:#cfdfef}main{max-width:1120px;margin:auto;padding:24px}
h1{margin:0;font-size:29px}h2{font-size:21px;margin:22px 0 12px}h3{font-size:16px}
.muted{color:#50657d;font-size:13px}.note{background:#fff8df;border-left:4px solid #9b7420;padding:14px 18px;margin:16px 0;line-height:1.5}
.grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}.metric,.panel{background:#fff;border:1px solid #dce4ed;border-radius:10px;padding:17px}
.metric strong{font-size:30px;display:block;color:#143e72}.metric span{font-size:13px;color:#596f83}
form{display:flex;align-items:end;gap:12px;flex-wrap:wrap;margin:14px 0}.form-field{display:flex;flex-direction:column;gap:5px}
label{font-weight:bold;font-size:13px}input,select{border:1px solid #becddd;border-radius:5px;padding:10px;background:#fff;min-width:140px;font:inherit;font-size:14px}
button{background:#1461ae;border:0;color:#fff;border-radius:5px;padding:11px 18px;font-weight:bold;cursor:pointer}
table{border-collapse:collapse;width:100%;font-size:14px}th,td{text-align:left;border-bottom:1px solid #e0e6ee;padding:12px 10px;vertical-align:top}th{background:#eaf0f6;color:#354c66}
.table-scroll{overflow-x:auto}small{font-size:12px}.tag{display:inline-block;border:1px solid #c5d5e6;background:#f0f5fb;border-radius:4px;font-size:12px;padding:3px 6px;white-space:nowrap}
.tag.proposal{background:#fef3df;border-color:#f0d7a5}.tag.rule{background:#e8f2ff}.tag.inspection{background:#e9e9ef}
pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f5f8fb;border:1px solid #dde5ee;border-radius:4px;padding:13px}
code{overflow-wrap:anywhere}dd{margin:2px 0 12px}dt{font-weight:bold;font-size:13px;color:#4b637c}
.footer{margin-top:24px;border-top:1px solid #cbd5df;padding-top:12px;color:#657a90;font-size:12px}
@media(max-width:760px){.grid{grid-template-columns:repeat(2,minmax(0,1fr))}main{padding:15px}table{font-size:12px}header{padding:20px 15px}}
"""


def h(value: object) -> str:
    return escape(str(value) if value is not None else '', quote=True)


def safe_external(url: object, *, pdf: bool = False) -> str | None:
    """Only make supplied government-source HTTP URLs clickable."""
    if not isinstance(url, str):
        return None
    parts = urlsplit(url)
    if parts.scheme != 'https' or parts.username or parts.password or parts.port is not None:
        return None
    permitted = {'www.govinfo.gov', 'govinfo.gov'} if pdf else {'www.federalregister.gov', 'federalregister.gov'}
    if parts.hostname not in permitted:
        return None
    return url


def links(review: dict) -> str:
    result = []
    for label, key, pdf in [('Federal Register', 'source_url', False), ('Official PDF', 'official_pdf_url', True)]:
        url = safe_external(review.get(key), pdf=pdf)
        if url:
            result.append(f'<a target="_blank" rel="noopener noreferrer" href="{h(url)}">{label}</a>')
    return ' · '.join(result) or 'No verified source URL available'


def read_cached_evidence(out_dir: Path, number: str) -> dict:
    """Find the newest *verified* evidence without modifying it. Safe doc/hash naming."""
    if not DOCUMENT_NUMBER_RE.fullmatch(number):
        raise ValueError('Invalid Federal Register document number')
    root = out_dir / number
    if not root.is_dir():
        return {'state': 'not_cached'}
    candidates = [p for p in root.glob('*.txt') if SHA256_RE.fullmatch(p.stem) and p.is_file() and not p.is_symlink()]
    candidates.sort(key=lambda p: p.stat().st_mtime_ns, reverse=True)
    if not candidates:
        return {'state': 'not_cached'}
    path = candidates[0]
    manifest_path = path.with_suffix('.json')
    if not manifest_path.is_file() or manifest_path.is_symlink():
        return {'state': 'manifest_missing'}
    try:
        raw = path.read_bytes()
        if len(raw) > 8_000_000:
            return {'state': 'oversized_cache'}
        if hashlib.sha256(raw).hexdigest() != path.stem:
            return {'state': 'hash_mismatch'}
        meta = json.loads(manifest_path.read_text(encoding='utf-8'))
        if not isinstance(meta, dict) or meta.get('document_number') != number or meta.get('sha256_bytes') != path.stem:
            return {'state': 'manifest_mismatch'}
        return {'state': 'hash_verified_local_cache', 'hash': path.stem,
                'bytes': len(raw), 'retrieved_at': meta.get('retrieved_at_utc'),
                'content': raw.decode('utf-8', errors='replace')}
    except (OSError, ValueError, UnicodeError, json.JSONDecodeError):
        return {'state': 'unreadable_cache'}


def title_page(label: str, inner: str) -> str:
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<meta name="referrer" content="no-referrer"><title>' + h(label) + ' | AeroCIE</title>'
            '<style>' + CSS + '</style></head><body>'
            '<header><h1>StrategicRisk Partners | AeroCIE</h1><p>Federal regulatory evidence · local research prototype</p></header>'
            '<main>' + inner + '<div class="footer">Source-linked preliminary intelligence only. '
            'No FAA certification, aircraft airworthiness clearance or verified compliance determination. '
            'Local read-only dashboard; not published on SRiskPartners.com.</div></main></body></html>')


def normalize_filters(params: dict[str, list[str]]) -> tuple[str, str, str, str]:
    keyword = (params.get('q', [''])[0] or '').strip()[:100]
    model = (params.get('model', [''])[0] or '').strip()[:64]
    category = (params.get('category', ['all'])[0] or 'all')
    if category not in ('all', 'rule', 'proposed_rule', 'notice', 'public_inspection', 'unclassified'):
        category = 'all'
    as_of = (params.get('as_of', [''])[0] or dt.datetime.now(dt.timezone.utc).date().isoformat())
    dt.date.fromisoformat(as_of)
    if model:
        validate_model(model)
    return keyword, model, category, as_of


def load_reviews(db_path: Path, *, keyword: str = '', category: str = 'all',
                 as_of: str | None = None, scan_limit: int = 1000) -> tuple[list[dict], list[dict], bool]:
    current = as_of or dt.datetime.now(dt.timezone.utc).date().isoformat()
    snapshots, truncated = latest_snapshots(db_path, scan_limit=scan_limit)
    matching = []
    for doc in snapshots:
        review = classify(doc, as_of=current)
        if category != 'all':
            if category == 'public_inspection':
                if doc.get('source') != 'public_inspection':
                    continue
            elif doc.get('source') == 'public_inspection' or review['publication_category'] != category:
                continue
        if keyword:
            searchable = ' '.join(str(doc.get(x) or '') for x in ('title', 'abstract', 'action', 'document_number'))
            if keyword.casefold() not in searchable.casefold():
                continue
        matching.append((doc, review))
    return [r for _, r in matching], [d for d, _ in matching], truncated


def render_index(db: Path, evidence_dir: Path, params: dict[str, list[str]]) -> str:
    q, model, category, as_of = normalize_filters(params)
    reviews, docs, truncated = load_reviews(db, keyword=q, category=category, as_of=as_of)
    visible = reviews[:MAX_VIEW_ROWS]
    matches = {}
    if model:
        screened = screen_documents(docs, model=model, as_of=as_of)
        matches = {r['document_number']: r['screening_result'] for r in screened['model_mentions']}
    counts = {'rule': 0, 'proposed_rule': 0, 'notice': 0, 'public_inspection': 0}
    for r in reviews:
        key = 'public_inspection' if r['source'] == 'public_inspection' else r['publication_category']
        if key in counts:
            counts[key] += 1
    opt = ''.join('<option value="' + h(v) + '"' + (' selected' if v == category else '') + '>' + h(label) + '</option>'
                  for v,label in [('all','All types'),('rule','Published rules'),('proposed_rule','Proposed rules'),
                                  ('notice','Notices'),('public_inspection','Public inspection'),('unclassified','Unclassified')])
    form = ('<section class="panel"><h2>Browse collected records</h2><form method="get" action="/">'
            '<div class="form-field"><label for="q">Search title/abstract</label><input id="q" name="q" maxlength="100" value="' + h(q) + '"></div>'
            '<div class="form-field"><label for="model">Model mention (optional)</label><input id="model" name="model" maxlength="64" placeholder="PW1100G" value="' + h(model) + '"></div>'
            '<div class="form-field"><label for="category">Publication type</label><select id="category" name="category">' + opt + '</select></div>'
            '<div class="form-field"><label for="as_of">As-of date (UTC)</label><input id="as_of" name="as_of" type="date" value="' + h(as_of) + '"></div>'
            '<button type="submit">Filter records</button></form></section>')
    metric_labels = [('Records in view', len(reviews)), ('Published rules', counts['rule']),
                     ('Proposed rules', counts['proposed_rule']), ('Public inspection', counts['public_inspection'])]
    metrics = '<div class="grid">' + ''.join('<div class="metric"><strong>' + str(n) + '</strong><span>' + h(lbl) + '</span></div>' for lbl,n in metric_labels) + '</div>'
    rows = []
    for r in visible:
        num = r['document_number']
        source = r['source']
        cat = 'public_inspection' if source == 'public_inspection' else r['publication_category']
        match = matches.get(num, 'No explicit model mention in stored metadata' if model else 'Not screened')
        detail = '/document/' + h(num) + ('?model=' + h(model) if model else '')
        rows.append('<tr><td><a href="' + detail + '">' + h(num) + '</a><br><small>' + h(r['publication_date'] or 'Unpublished') + '</small></td>'
                    '<td>' + h(r['title']) + '</td><td><span class="tag ' + h('proposal' if cat == 'proposed_rule' else 'rule' if cat == 'rule' else 'inspection') + '">' + h(cat.replace('_',' ')) + '</span></td>'
                    '<td>' + h(r.get('reported_effective_on') or 'Not reported') + '</td><td>' + h(match.replace('_',' ')) + '</td><td>' + links(r) + '</td></tr>')
    if not rows:
        rows = ['<tr><td colspan="6">No records match this filter. This does NOT mean the model has no applicable rules.</td></tr>']
    info = ('<p class="muted">Showing ' + str(len(visible)) + ' of ' + str(len(reviews)) + ' matching latest snapshots.'
            + (' Scan limited to 1,000 newest snapshots; results are incomplete.' if truncated else '') +
            ' Model screening covers stored metadata only; select a document to inspect any cached full-text evidence.</p>')
    note = ('<div class="note"><strong>Research triage—not verified legal status or applicability.</strong> '
            'A listed document is not necessarily a new obligation; a missing model mention is never a clearance. '
            'Dates are as reported by the collected source and require authoritative verification. '
            'This interface reads your existing local database and does not update it.</div>')
    table = '<section class="panel"><h2>Regulatory review queue</h2>' + info + '<div class="table-scroll"><table><thead><tr>' + ''.join('<th>' + c + '</th>' for c in ('Document','Subject','Type','Reported effective','Model evidence','Sources')) + '</tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div></section>'
    return title_page('Regulatory review queue', note + metrics + form + table)


def render_document(db: Path, evidence_dir: Path, number: str, params: dict[str, list[str]]) -> str:
    if not DOCUMENT_NUMBER_RE.fullmatch(number):
        raise ValueError('Invalid document number')
    model = (params.get('model', [''])[0] or '').strip()[:64]
    if model:
        validate_model(model)
    as_of = (params.get('as_of', [''])[0] or dt.datetime.now(dt.timezone.utc).date().isoformat())
    dt.date.fromisoformat(as_of)
    _, docs, truncated = load_reviews(db, as_of=as_of)
    doc = next((x for x in docs if x.get('document_number') == number and x.get('source') == 'published'), None)
    if not doc:
        return title_page('Not collected', '<h2>Document not found in published collection</h2><p><a href="/">Back to queue</a></p>')
    r = classify(doc, as_of=as_of)
    data = read_cached_evidence(evidence_dir, number)
    summary = ('<p><a href="/">← Back to queue</a></p><h2>' + h(r['title']) + '</h2>'
               '<div class="note">Preliminary review only. Aircraft applicability and compliance remain unverified. '
               'Confirm current FAA DRS, revisions, incorporated material and asset records.</div>')
    fields = [('Document', number), ('Publication type', r['publication_category']), ('Status for triage',r['triage_status']),
              ('Publication date',r['publication_date']),('Reported effective date',r['reported_effective_on'] or 'Not reported'),
              ('Source action',r['agency_action'] or 'Not reported'),('Regulatory docket', ', '.join(r['docket_ids'] or []) or 'Not reported')]
    summary += '<section class="panel"><dl>' + ''.join('<dt>' + h(k) + '</dt><dd>' + h(v) + '</dd>' for k,v in fields) + '</dl><p>' + links(r) + '</p></section>'
    note = {'not_cached':'No local full-text copy saved. Use AeroCIE-004 collector separately.',
            'hash_verified_local_cache':'Saved full text independently checked against its SHA-256 filename.',
            'hash_mismatch':'Evidence file hash mismatch. Do not rely on cached text.',
            'manifest_mismatch':'Evidence manifest disagrees with the file/document. Review manually.',
            'manifest_missing':'Evidence metadata is missing; review manually.',
            'oversized_cache':'Evidence exceeds supported size.',
            'unreadable_cache':'Evidence unreadable; review manually.'}.get(data['state'], 'Evidence requires review')
    summary += '<section class="panel"><h2>Archived source evidence</h2><p>' + h(note) + '</p>'
    if data['state'] == 'hash_verified_local_cache':
        summary += '<p><strong>SHA-256:</strong> <code>' + h(data['hash']) + '</code><br><strong>Size:</strong> ' + str(data['bytes']) + ' bytes<br><strong>Retrieved:</strong> ' + h(data['retrieved_at']) + '</p>'
    summary += '</section>'
    if model:
        summary += '<section class="panel"><h2>Model research: ' + h(model) + '</h2>'
        meta_result = screen_documents([doc],model=model,as_of=as_of)
        summary += '<p>Stored metadata exact-name mentions: ' + str(meta_result['model_mention_count']) + ' document(s).</p>'
        if data['state'] == 'hash_verified_local_cache':
            assessment = screen_full_text(data['content'], model)
            summary += '<p><strong>Full-text screening:</strong> ' + h(assessment['screening_result'].replace('_',' ')) + '</p>'
            summary += ('<p><strong>Exact model mentions:</strong> ' + str(assessment['total_model_mentions']) +
                        ' &nbsp; <strong>Variant candidates:</strong> ' + str(assessment['family_variant_candidate_count']) + '</p>')
            if assessment['family_variant_candidates']:
                summary += '<h3>Family-name heuristic candidates in applicability section</h3><p>' + ', '.join('<code>' + h(x['candidate_variant']) + '</code>' for x in assessment['family_variant_candidates']) + '</p>'
            if assessment['sample_evidence']:
                summary += '<h3>Example text evidence</h3>' + ''.join('<pre>' + h(x['excerpt']) + '</pre>' for x in assessment['sample_evidence'][:3])
            summary += '<p class="muted">Variant matching is a naming-pattern research heuristic, not an authoritative type-certificate mapping. '
            summary += 'No compliance or engine-specific airworthiness result is produced.</p>'
        else:
            summary += '<p>No verified cached full text available for detailed model analysis.</p>'
        summary += '</section>'
    return title_page('Document '+number, summary)


def make_handler(db: Path, evidence_dir: Path, *, port: int):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            # Prevent Host-header based DNS-rebinding access to local data.
            if self.headers.get('Host', '') not in (f'127.0.0.1:{port}', f'localhost:{port}'):
                return self.respond(403, 'Forbidden', '<p>Unrecognized Host header</p>')
            path = urlsplit(self.path)
            params = parse_qs(path.query, keep_blank_values=True, max_num_fields=12)
            try:
                if path.path == '/':
                    page = render_index(db, evidence_dir, params)
                elif re.fullmatch(r'/document/\d{4}-\d{4,6}',path.path):
                    page = render_document(db, evidence_dir,path.path.split('/')[-1],params)
                else:
                    return self.respond(404, 'Not found', '<p>Page not found</p>')
                return self.respond(200, 'AeroCIE', page)
            except (ValueError, FileNotFoundError, sqlite3.Error, json.JSONDecodeError) as exc:
                return self.respond(400, 'Data unavailable', '<h2>Cannot show the requested view</h2><p>' + h(exc) + '</p>')

        def do_POST(self):
            self.respond(405, 'Read-only', '<p>This dashboard does not accept changes.</p>')

        def respond(self, status: int, label: str, body: str):
            page = body if body.startswith('<!doctype html>') else title_page(label, body)
            raw = page.encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(raw)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('X-Frame-Options','DENY')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Content-Security-Policy', "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(raw)

        def log_message(self, format, *args):
            return  # avoid logging query parameters containing customer searches

    return Handler


def main(argv=None):
    p = argparse.ArgumentParser(description='AeroCIE-005: local offline regulatory evidence dashboard (read-only)')
    p.add_argument('--db', type=Path, default=Path('build/aerocie/federal_register.sqlite3'))
    p.add_argument('--evidence-dir', type=Path, default=Path('build/aerocie/full_text_evidence'))
    p.add_argument('--port', type=int, default=8765)
    p.add_argument('--open', action='store_true', help='Open the local page in your default browser')
    args = p.parse_args(argv)
    if not (1 <= args.port <= 65535):
        p.error('port must be between 1 and 65535')
    if not args.db.is_file():
        print(f'No AeroCIE database found: {args.db}\nRun fr_collector first or specify --db.', file=sys.stderr)
        return 1
    try:
        # Validate before launching a server.
        latest_snapshots(args.db,scan_limit=1)
        address = f'http://127.0.0.1:{args.port}/'
        with ThreadingHTTPServer(('127.0.0.1',args.port), make_handler(args.db,args.evidence_dir,port=args.port)) as server:
            print('AeroCIE local dashboard: '+address,flush=True)
            print('Offline, read-only, loopback only. Press Ctrl+C to stop.',flush=True)
            if args.open:
                webbrowser.open(address)
            try:
                server.serve_forever(poll_interval=0.25)
            except KeyboardInterrupt:
                print('\nAeroCIE dashboard stopped.')
        return 0
    except (OSError, sqlite3.Error, ValueError) as exc:
        print(f'AeroCIE dashboard error: {exc}',file=sys.stderr)
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
