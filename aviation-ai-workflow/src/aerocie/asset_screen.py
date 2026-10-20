"""AeroCIE-003: read-only asset/model mention screening of Federal Register metadata.

RESEARCH TRIAGE ONLY: A reference to a model in document metadata does not
establish that an asset is affected or compliant. Nonmatches are NOT clearances.
The collector currently stores metadata rather than full regulatory text.

Python standard library only. Does not mutate the AeroCIE database, fetch data,
or determine aircraft-specific legal/technical applicability.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import csv
import datetime as dt
import io
import json
from pathlib import Path
import re
import sqlite3
import sys
from typing import Any

from .review_queue import classify

# Constrain user-specified identifiers and names; do not treat arbitrary regex as input.
MODEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9./_-]{2,63}$")
MAX_SCAN = 5000
SEARCH_FIELDS = ("title", "abstract", "action")


def validate_model(model: str) -> str:
    model = model.strip()
    if not MODEL_RE.fullmatch(model):
        raise ValueError("Model must be 3–64 letters/digits or . / _ -; e.g. PW1100G or A320-200")
    return model


def bounded_pattern(phrase: str) -> re.Pattern[str]:
    """Match model/manufacturer as tokens; PW1100G must not match PW1100G2."""
    return re.compile(r"(?<![A-Za-z0-9])" + re.escape(phrase) + r"(?![A-Za-z0-9])", re.IGNORECASE)


def source_context(doc: dict[str, Any], phrase: str) -> dict[str, str] | None:
    pattern = bounded_pattern(phrase)
    for field in SEARCH_FIELDS:
        value = doc.get(field)
        if not isinstance(value, str) or not value:
            continue
        match = pattern.search(value)
        if match:
            lo = max(0, match.start() - 90)
            hi = min(len(value), match.end() + 90)
            excerpt = ("…" if lo else "") + value[lo:hi].replace("\n", " ") + ("…" if hi < len(value) else "")
            return {"field": field, "excerpt": excerpt}
    return None


def latest_snapshots(db_path: Path, *, scan_limit: int = 1000) -> tuple[list[dict[str, Any]], bool]:
    if not db_path.is_file():
        raise FileNotFoundError(f"No AeroCIE database found at: {db_path}")
    if scan_limit < 1 or scan_limit > MAX_SCAN:
        raise ValueError(f"--scan-limit must be between 1 and {MAX_SCAN}")
    # Explicit closing is essential on Windows: sqlite3's transaction context
    # manager does NOT close the database file handle.
    uri = f"file:{db_path.resolve().as_posix()}?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as connection:
        present = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='document_snapshots'"
        ).fetchone()
        if not present:
            raise ValueError("Database does not contain document_snapshots")
        rows = connection.execute("""
            SELECT s.payload_json FROM document_snapshots AS s
            INNER JOIN (
               SELECT source, document_number, MAX(id) AS latest_id
               FROM document_snapshots GROUP BY source, document_number
            ) AS d ON s.id=d.latest_id
            ORDER BY s.id DESC LIMIT ?
        """, (scan_limit + 1,)).fetchall()
    truncated = len(rows) > scan_limit
    result = []
    for (payload,) in rows[:scan_limit]:
        data = json.loads(payload)
        if not isinstance(data, dict):
            raise ValueError("Stored snapshot is not an object")
        result.append(data)
    return result, truncated


def screen_documents(
    docs: list[dict[str, Any]], *, model: str,
    manufacturer: str | None = None,
    aliases: tuple[str, ...] = (),
    as_of: str | None = None,
    include_context: bool = True,
) -> dict[str, Any]:
    """Find explicit model mentions and lesser manufacturer-only research leads."""
    model = validate_model(model)
    current_date = as_of or dt.datetime.now(dt.timezone.utc).date().isoformat()
    dt.date.fromisoformat(current_date)
    manufacturers = []
    for name in ([manufacturer] if manufacturer else []) + list(aliases):
        if not isinstance(name, str) or not (name := name.strip()) or len(name) > 80:
            raise ValueError("Manufacturer or alias must be non-empty and at most 80 characters")
        if name.casefold() not in [n.casefold() for n in manufacturers]:
            manufacturers.append(name)
    exact_models = []
    manufacturer_context = []
    for doc in docs:
        review = classify(doc, as_of=current_date)
        match = source_context(doc, model)
        found_brand = None
        for name in manufacturers:
            found_brand = source_context(doc, name)
            if found_brand:
                break
        if match:
            exact_models.append({**review,
                "screening_result": "model_explicitly_mentioned_in_stored_metadata",
                "matched_model": model,
                "evidence_field": match["field"],
                "evidence_excerpt": match["excerpt"],
                "asset_applicability_verified": False,
                "review_required": True,
            })
        elif found_brand and include_context:
            manufacturer_context.append({**review,
                "screening_result": "manufacturer_mention_only_not_model_match",
                "matched_model": None,
                "evidence_field": found_brand["field"],
                "evidence_excerpt": found_brand["excerpt"],
                "asset_applicability_verified": False,
                "review_required": True,
            })
    return {
        "as_of": current_date,
        "requested_model": model,
        "requested_manufacturer": manufacturer,
        "manufacturer_aliases": list(aliases),
        "records_scanned": len(docs),
        "model_mention_count": len(exact_models),
        "manufacturer_context_count": len(manufacturer_context),
        "model_mentions": exact_models,
        "manufacturer_context_only": manufacturer_context,
        "asset_applicability_verified": False,
        "limitations": (
            "Screens only the title, abstract and action fields in locally stored "
            "Federal Register metadata. The absence of a model mention is NOT proof "
            "that no applicable directive exists. A mention is NOT proof of applicability. "
            "Check the full official rule, FAA DRS, current revisions, exact model, "
            "part/serial records, exclusions, and compliance requirements with qualified review."
        ),
    }


def safe_csv_value(value: Any) -> Any:
    """Prevent spreadsheet formula execution when exporting untrusted source text."""
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def write_csv(items: dict[str, Any]) -> str:
    output = io.StringIO(newline="")
    fields = ["screening_result", "document_number", "title", "publication_category",
              "triage_status", "publication_date", "reported_effective_on",
              "matched_model", "evidence_field", "evidence_excerpt", "source_url",
              "official_pdf_url", "asset_applicability_verified", "review_required"]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for key in ("model_mentions", "manufacturer_context_only"):
        for row in items[key]:
            writer.writerow({name: safe_csv_value(row.get(name)) for name in fields})
    return output.getvalue()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="AeroCIE-003: review-only engine/aircraft model metadata screening")
    p.add_argument("--model", required=True, help="Exact engine/aircraft model identifier, e.g. PW1100G")
    p.add_argument("--manufacturer", default=None, help="Optional manufacturer name for secondary research leads")
    p.add_argument("--manufacturer-alias", action="append", default=[],
                   help="Explicit additional manufacturer spellings; repeat as needed")
    p.add_argument("--as-of", default=None, help="As-of YYYY-MM-DD for reproducible triage")
    p.add_argument("--db", type=Path, default=Path("build/aerocie/federal_register.sqlite3"))
    p.add_argument("--scan-limit", type=int, default=1000)
    p.add_argument("--format", choices=("json", "csv"), default="json")
    p.add_argument("--out", type=Path, default=None, help="Optional export path")
    args = p.parse_args(argv)
    try:
        snapshots, truncated = latest_snapshots(args.db, scan_limit=args.scan_limit)
        result = screen_documents(
            snapshots, model=args.model, manufacturer=args.manufacturer,
            aliases=tuple(args.manufacturer_alias), as_of=args.as_of)
        result["scan_truncated"] = truncated
        if truncated:
            result["limitations"] += " The local database scan was truncated; increase --scan-limit if needed."
        content = write_csv(result) if args.format == "csv" else json.dumps(result, indent=2, ensure_ascii=False)
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(content, encoding="utf-8")
            print(f"Exported {result['model_mention_count']} model mentions and "
                  f"{result['manufacturer_context_count']} manufacturer-only leads to {args.out}")
        else:
            print(content)
        return 0
    except (ValueError, FileNotFoundError, sqlite3.Error, json.JSONDecodeError, OSError) as exc:
        print(f"AeroCIE asset-screen error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
