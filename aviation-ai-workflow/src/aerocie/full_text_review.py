"""AeroCIE-004: archived full-text evidence and conservative model mention triage.

Standard library only. This is research triage, NEVER airworthiness/compliance
verification. The FederalRegister.gov text is an informational rendering;
verify legally operative text against the official Federal Register edition and
current FAA DRS, including corrections, supersedures and incorporated material.

Does not modify the existing AeroCIE SQLite database.
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
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable

from .asset_screen import bounded_pattern, validate_model
from .review_queue import classify
from .fr_collector import DOC_ID_RE

MAX_TEXT_BYTES = 8_000_000
USER_AGENT = 'SRP-AeroCIE-Prototype/0.4 (regulatory-research; no automatic compliance decisions)'
RAW_PATH_RE = re.compile(r'^/documents/full_text/text/(\d{4})/(\d{2})/(\d{2})/(\d{4}-\d{4,6})\.txt$')
SECTION_HEADING_RE = re.compile(r'(?im)^\s*(?:\([a-z]\)\s*)?(Applicability|Unsafe Condition|Compliance|Required Actions)\s*[:.]?\s*$')
NEXT_LETTER_HEADING = re.compile(r'(?m)^\s*\([a-z]\)\s+[A-Z][^\n]{1,85}\s*$')

# Deliberately LIMITED research heuristics, NOT type-certificate/FAA-approved
# mappings. Only identify candidates when these model-like tokens occur inside
# a detected (c) Applicability paragraph. Unknown families are not extrapolated.
FAMILY_VARIANT_PATTERNS = {
    'PW1100G': re.compile(r'(?<![A-Z0-9])PW11[0-9]{2}[A-Z0-9]*-JM(?![A-Z0-9])', re.IGNORECASE),
    'PW1400G': re.compile(r'(?<![A-Z0-9])PW14[0-9]{2}[A-Z0-9]*-JM(?![A-Z0-9])', re.IGNORECASE),
}



class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req: urllib.request.Request, fp: Any, code: int,
                         msg: str, headers: Any, newurl: str) -> None:
        raise ValueError('Unexpected redirect; raw-text source requires manual review')


def raw_text_url(document: dict[str, Any]) -> str:
    """Return tightly allowlisted Federal Register raw-text link for a published document."""
    number = document.get('document_number')
    date = document.get('publication_date')
    if not isinstance(number, str) or not DOC_ID_RE.fullmatch(number):
        raise ValueError('Invalid Federal Register document number')
    if document.get('source') != 'published':
        raise ValueError('Only published Federal Register documents can be reviewed here')
    try:
        parsed_date = dt.date.fromisoformat(date)
    except (ValueError, TypeError) as exc:
        raise ValueError('Missing or invalid publication date') from exc
    default = f'https://www.federalregister.gov/documents/full_text/text/{parsed_date:%Y/%m/%d}/{number}.txt'
    url = document.get('raw_text_url') or default
    if not isinstance(url, str):
        raise ValueError('Malformed raw-text URL')
    parsed = urllib.parse.urlsplit(url)
    if (parsed.scheme != 'https' or parsed.hostname not in ('www.federalregister.gov', 'federalregister.gov')
            or parsed.username or parsed.password or parsed.port is not None or parsed.query or parsed.fragment):
        raise ValueError('Unsafe or unexpected raw-text URL origin')
    match = RAW_PATH_RE.fullmatch(parsed.path)
    if not match or match.group(4) != number or '/'.join(match.groups()[:3]) != parsed_date.strftime('%Y/%m/%d'):
        raise ValueError('Raw-text URL does not match this document and publication date')
    return url


def download_text(url: str, *, timeout: int = 25) -> bytes:
    """Download from validated FR origin; deny redirects and oversize payloads."""
    # Validate URL a second time even if injected/used outside raw_text_url.
    parsed = urllib.parse.urlsplit(url)
    if (parsed.scheme != 'https' or parsed.hostname not in ('www.federalregister.gov', 'federalregister.gov')
            or parsed.username or parsed.password or parsed.port is not None
            or not RAW_PATH_RE.fullmatch(parsed.path) or parsed.query or parsed.fragment):
        raise ValueError('Only canonical FederalRegister.gov raw-text URLs are permitted')
    request = urllib.request.Request(url, headers={'Accept': 'text/plain', 'User-Agent': USER_AGENT})
    opener = urllib.request.build_opener(NoRedirect())
    with opener.open(request, timeout=timeout) as response:
        data = response.read(MAX_TEXT_BYTES + 1)
        if len(data) > MAX_TEXT_BYTES:
            raise ValueError('Document exceeds maximum full-text size (8 MB)')
        if not data or b'\x00' in data:
            raise ValueError('Empty or non-text response from Federal Register')
        return data


def read_published_snapshot(db_path: Path, number: str) -> dict[str, Any]:
    if not DOC_ID_RE.fullmatch(number):
        raise ValueError('Invalid document number; expected e.g. 2024-06419')
    if not db_path.is_file():
        raise FileNotFoundError(f'No AeroCIE database found: {db_path}')
    uri = f'file:{db_path.resolve().as_posix()}?mode=ro'
    with closing(sqlite3.connect(uri, uri=True)) as conn:
        row = conn.execute('''
            SELECT payload_json FROM document_snapshots
            WHERE source='published' AND document_number=?
            ORDER BY id DESC LIMIT 1
        ''', (number,)).fetchone()
    if row is None:
        raise ValueError(f'No locally collected PUBLISHED document {number}; run the collector first')
    document = json.loads(row[0])
    if not isinstance(document, dict):
        raise ValueError('Invalid stored document snapshot')
    return document


def excerpt(text: str, start: int, end: int, *, context: int = 135) -> str:
    lo, hi = max(0, start - context), min(len(text), end + context)
    content = re.sub(r'\s+', ' ', text[lo:hi]).strip()
    return ('…' if lo else '') + content + ('…' if hi < len(text) else '')


def applicability_spans(text: str) -> list[tuple[int, int]]:
    spans = []
    for heading in SECTION_HEADING_RE.finditer(text):
        if heading.group(1).lower() != 'applicability':
            continue
        next_section = NEXT_LETTER_HEADING.search(text, heading.end())
        end = next_section.start() if next_section else min(len(text), heading.end() + 8000)
        # Bounding prevents accidentally considering entire regulatory publications
        # applicability text when headings cannot be parsed reliably.
        end = min(end, heading.end() + 8000)
        spans.append((heading.start(), end))
    return spans


def screen_full_text(text: str, model: str) -> dict[str, Any]:
    model = validate_model(model)
    pattern = bounded_pattern(model)
    spans = applicability_spans(text)
    matches = list(pattern.finditer(text))
    detailed = []
    for match in matches[:10]:
        is_applicability = any(begin <= match.start() < end for begin, end in spans)
        detailed.append({
            'evidence_area': 'candidate_applicability_section' if is_applicability else 'elsewhere_in_document',
            'character_offset': match.start(),
            'excerpt': excerpt(text, match.start(), match.end()),
        })
    in_section = sum(any(begin <= m.start() < end for begin, end in spans) for m in matches)
    family_regex = FAMILY_VARIANT_PATTERNS.get(model.upper())
    family_candidates = []
    if family_regex is not None:
        seen_candidates = set()
        for begin, end in spans:
            for found in family_regex.finditer(text, begin, end):
                variant = found.group().upper()
                if variant in seen_candidates:
                    continue
                seen_candidates.add(variant)
                family_candidates.append({
                    'candidate_variant': variant,
                    'evidence_area': 'candidate_applicability_section',
                    'character_offset': found.start(),
                    'excerpt': excerpt(text, found.start(), found.end()),
                })
    # Report all distinct candidates (typically fewer than 25 for an AD), but
    # avoid unlimited output on unusually large, malformed or repeated text.
    family_count = len(family_candidates)
    family_evidence = family_candidates[:30]
    if in_section:
        result = 'model_mentioned_in_candidate_applicability_section_review_required'
    elif family_count:
        result = 'series_variant_candidates_in_applicability_review_required'
    elif matches:
        result = 'model_mentioned_elsewhere_full_text_review_required'
    else:
        result = 'no_explicit_model_mention_in_this_document_not_clearance'
    return {
        'screening_result': result,
        'requested_model': model,
        'total_model_mentions': len(matches),
        'mentions_in_candidate_applicability_section': in_section,
        'applicability_headings_identified': len(spans),
        'family_variant_candidate_count': family_count,
        'family_variant_candidates': family_evidence,
        'family_variant_candidates_truncated': family_count > len(family_evidence),
        'family_variant_matching_basis': (
            'limited PW11xx/PW14xx name-pattern research heuristic; '
            'not an authoritative or verified type-certificate mapping'
            if family_regex is not None else 'no series-to-variant heuristic configured'
        ),
        'sample_evidence': detailed,
        'evidence_samples_truncated': len(matches) > len(detailed),
        'asset_applicability_verified': False,
        'review_required': True,
    }


def evidence_dir(out_dir: Path, doc_number: str) -> Path:
    if not DOC_ID_RE.fullmatch(doc_number):
        raise ValueError('Invalid document number')
    return out_dir / doc_number


def write_evidence(out_dir: Path, doc: dict[str, Any], source_url: str,
                   payload: bytes, *, retrieved_at: str) -> tuple[Path, Path, str, bool]:
    """Immutable content-addressed evidence files. Never overwrite a different body."""
    digest = hashlib.sha256(payload).hexdigest()
    root = evidence_dir(out_dir, doc['document_number'])
    root.mkdir(parents=True, exist_ok=True)
    content_path = root / f'{digest}.txt'
    meta_path = root / f'{digest}.json'
    if content_path.exists():
        if hashlib.sha256(content_path.read_bytes()).hexdigest() != digest:
            raise ValueError(f'Hash mismatch in existing evidence file: {content_path}')
        new_snapshot = False
    else:
        content_path.write_bytes(payload)
        new_snapshot = True
    if not meta_path.exists():
        manifest = {
            'document_number': doc['document_number'],
            'publication_date': doc.get('publication_date'),
            'retrieved_at_utc': retrieved_at,
            'source_url': source_url,
            'document_html_url': doc.get('html_url'),
            'official_pdf_url_for_manual_verification': doc.get('pdf_url'),
            'sha256_bytes': digest,
            'byte_count': len(payload),
            'original_text_encoding_assumption': 'UTF-8 with replacement for invalid bytes on reading',
            'legal_status': 'FederalRegister.gov text is informational; verify official publication and FAA DRS',
        }
        meta_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    return content_path, meta_path, digest, new_snapshot


def select_offline_snapshot(out_dir: Path, number: str) -> tuple[bytes, str, Path]:
    root = evidence_dir(out_dir, number)
    files = sorted(root.glob('*.txt'), key=lambda p: p.stat().st_mtime_ns, reverse=True) if root.exists() else []
    if not files:
        raise FileNotFoundError(f'No offline full-text evidence cached for {number}')
    path = files[0]
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != path.stem:
        raise ValueError(f'Cached full-text evidence failed SHA-256 validation: {path}')
    manifest = path.with_suffix('.json')
    if not manifest.is_file():
        raise ValueError(f'Evidence manifest missing: {manifest}')
    metadata = json.loads(manifest.read_text(encoding='utf-8'))
    url = metadata.get('source_url')
    if not isinstance(url, str):
        raise ValueError('Cached manifest missing source_url')
    return raw, url, manifest


def run(db_path: Path, number: str, model: str, out_dir: Path, *,
        as_of: str | None = None, offline: bool = False,
        fetcher: Callable[[str], bytes] = download_text,
        now: Callable[[], str] | None = None) -> dict[str, Any]:
    date = as_of or dt.datetime.now(dt.timezone.utc).date().isoformat()
    dt.date.fromisoformat(date)
    doc = read_published_snapshot(db_path, number)
    url = raw_text_url(doc)
    retrieved_at = (now or (lambda: dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')))()
    if offline:
        body, stored_url, manifest_path = select_offline_snapshot(out_dir, number)
        if stored_url != url:
            raise ValueError('Cached source URL no longer agrees with local document metadata')
        content_path = manifest_path.with_suffix('.txt')
        digest = hashlib.sha256(body).hexdigest()
        new = False
        evidence_state = 'cached_offline_not_rechecked_against_source'
    else:
        body = fetcher(url)
        if not isinstance(body, bytes) or not body or len(body) > MAX_TEXT_BYTES:
            raise ValueError('Full text must be non-empty bytes within the size limit')
        if b'\x00' in body:
            raise ValueError('Full-text response is not a plain-text document')
        content_path, manifest_path, digest, new = write_evidence(
            out_dir, doc, url, body, retrieved_at=retrieved_at)
        evidence_state = 'new_full_text_hash_stored' if new else 'identical_full_text_hash_seen_before'
    text = body.decode('utf-8', errors='replace')
    category = classify(doc, as_of=date)
    screening = screen_full_text(text, model)
    return {
        'document_number': number,
        'title': doc.get('title'),
        'as_of': date,
        'document_type': category['document_type'],
        'publication_category': category['publication_category'],
        'triage_status': category['triage_status'],
        'publication_date': doc.get('publication_date'),
        'reported_effective_on': doc.get('effective_on'),
        'reported_dates_text': doc.get('dates_text'),
        'federal_register_url': doc.get('html_url'),
        'official_pdf_url_for_manual_verification': doc.get('pdf_url'),
        'retrieved_full_text_url': url,
        'sha256': digest,
        'bytes_saved': len(body),
        'evidence_state': evidence_state,
        'evidence_text_path': str(content_path),
        'evidence_manifest_path': str(manifest_path),
        'decoding_note': 'Source contained invalid UTF-8 bytes' if '\ufffd' in text else None,
        **screening,
        'limitations': (
            'Candidate text matching only, not an applicability or compliance determination. '
            'Raw FederalRegister.gov text is informational and may omit incorporated-by-reference material; '
            'verify official Federal Register PDF and current FAA DRS, amendments, models/variants, parts, '
            'serial ranges, compliance dates, exclusions, and maintenance records with qualified review. '
            'Any proposed series/variant relationship is an unverified naming heuristic, NOT a model applicability finding. '
            'A text change is not automatically a change in the law, and a nonmatch is NOT clearance.'
        ),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description='AeroCIE-004: full text evidence and model mention triage')
    p.add_argument('--document-number', required=True, help='Previously collected published FR number, e.g. 2024-06419')
    p.add_argument('--model', required=True, help='Model mention to find, e.g. PW1100G')
    p.add_argument('--db', type=Path, default=Path('build/aerocie/federal_register.sqlite3'))
    p.add_argument('--evidence-dir', type=Path, default=Path('build/aerocie/full_text_evidence'))
    p.add_argument('--as-of', default=None, help='As-of date YYYY-MM-DD; regulatory triage only')
    p.add_argument('--offline', action='store_true', help='Read saved evidence only; do not contact API')
    p.add_argument('--report-out', type=Path, default=None, help='Optional path for JSON report')
    args = p.parse_args(argv)
    try:
        result = run(args.db, args.document_number, args.model, args.evidence_dir,
                     as_of=args.as_of, offline=args.offline)
        body = json.dumps(result, indent=2, ensure_ascii=False)
        if args.report_out:
            args.report_out.parent.mkdir(parents=True, exist_ok=True)
            args.report_out.write_text(body, encoding='utf-8')
            print(f'Wrote review report to {args.report_out}')
        else:
            print(body)
        return 0
    except (ValueError, FileNotFoundError, OSError, urllib.error.URLError,
            urllib.error.HTTPError, sqlite3.Error, json.JSONDecodeError) as exc:
        print(f'AeroCIE full-text review error: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
