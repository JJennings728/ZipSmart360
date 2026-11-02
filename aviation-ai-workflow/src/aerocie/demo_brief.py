"""AeroCIE-015: offline synthetic-only internal product demonstration."""
from __future__ import annotations
import argparse
from html import escape
import json
from pathlib import Path
import re
import sys
from .audit_packet import CHECKS, _official_url
from .review_journal import _packet, summary

STATES = {"PENDING_HUMAN_REVIEW", "CHECKED_RESEARCH_ONLY", "FOLLOW_UP_REQUIRED"}


def e(value: object) -> str:
    return escape(str(value) if value is not None else "", quote=True)


def build_preview(packet_path: Path, journal_path: Path | None = None) -> dict:
    packet = _packet(packet_path)
    subject = packet.get("research_candidate")
    if not isinstance(subject, dict):
        raise ValueError("Missing research subject")
    if not (isinstance(subject.get("subject_id"), str)
            and subject["subject_id"].startswith("demo:")
            and isinstance(subject.get("subject_label"), str)
            and subject["subject_label"].lower().startswith("synthetic ")):
        raise ValueError("Internal demonstration accepts synthetic subject only")
    if packet.get("applicability_status") != "NOT_DETERMINED":
        raise ValueError("Unsupported applicability claim")
    checks = (summary(packet_path, journal_path)["latest_checklist_states"]
              if journal_path is not None
              else {key: "PENDING_HUMAN_REVIEW" for key, _ in CHECKS})
    if set(checks) != {key for key, _ in CHECKS} or any(v not in STATES for v in checks.values()):
        raise ValueError("Invalid review states")
    documents = []
    for record in packet.get("published_metadata_documents", []):
        number = record.get("document_number")
        if not isinstance(number, str) or not re.fullmatch(r"\d{4}-\d{4,6}", number):
            raise ValueError("Invalid document number")
        documents.append({
            "number": number,
            "title": record.get("title"),
            "published": record.get("publication_date"),
            "effective": record.get("stated_effective_on"),
            "fingerprint": record.get("source_sha256"),
            "local_state": record.get("source_integrity_status"),
            "url": (None if record.get("source_integrity_status") == "SYNTHETIC_FIXTURE_NOT_VERIFIED" else _official_url(record.get("official_link_format_checked_only"))),
        })
    if not documents:
        raise ValueError("No publications to demonstrate")
    corrections = []
    for edge in packet.get("correction_candidates_research_only", []):
        corrections.append({
            "from": edge.get("correcting_document_number"),
            "to": edge.get("earlier_document_number"),
            "state": edge.get("evidence_status"),
        })
    return {
        "subject": subject["subject_label"],
        "rationale": subject.get("rationale", ""),
        "documents": documents,
        "corrections": corrections,
        "checks": [{"id": key, "instruction": desc, "state": checks[key]}
                   for key, desc in CHECKS],
        "as_of": packet.get("as_of_calendar_date"),
        "packet_hash": packet["audit_sha256"],
        "review_disposition": "HOLD_FOR_HUMAN_REVIEW",
        "applicability_status": "NOT_DETERMINED",
        "compliance_status": "NOT_DETERMINED",
        "external_release_authorized": False,
    }


def render_html(data: dict) -> str:
    if (data.get("review_disposition") != "HOLD_FOR_HUMAN_REVIEW"
            or data.get("compliance_status") != "NOT_DETERMINED"
            or data.get("external_release_authorized") is not False):
        raise ValueError("Unsafe demo state")
    if len(data.get("checks", [])) != len(CHECKS) or any(
            c.get("state") not in STATES for c in data["checks"]):
        raise ValueError("Invalid checklist status")
    completed = sum(c["state"] == "CHECKED_RESEARCH_ONLY" for c in data["checks"])
    unresolved = len(CHECKS) - completed
    docs = []
    for d in data["documents"]:
        link = ('<a href="' + e(d["url"])
                + '" target="_blank" rel="noopener noreferrer" referrerpolicy="no-referrer">'
                'View official publication</a>' if _official_url(d["url"])
                else "Official link unavailable")
        docs.append(
            '<article><h3>' + e(d["number"]) + ' | ' + e(d["title"])
            + '</h3><p>Published: ' + e(d["published"])
            + ' | Stated effective: ' + e(d["effective"])
            + '</p><p>Local evidence state: ' + e(d["local_state"])
            + '</p><p>Local SHA-256: <code>' + e(d["fingerprint"])
            + '</code></p><p>' + link + '</p></article>'
        )
    edges = ''.join('<li>' + e(edge["from"]) + ' CORRECTS ' + e(edge["to"])
                    + ' | ' + e(edge["state"]) + ' | RESEARCH ONLY</li>'
                    for edge in data["corrections"])
    rows = ''.join('<tr><td>' + e(c["id"]) + '</td><td>'
                   + e(c["instruction"]) + '</td><td>'
                   + e(c["state"]) + '</td></tr>'
                   for c in data["checks"])
    css = (
        'body{font:15px/1.55 Montserrat,Arial,sans-serif;max-width:1080px;'
        'padding:24px;margin:auto;color:#142e48;background:#f5f7fa}'
        'h1{font-size:28px}h2{margin-top:28px}header{border-bottom:4px solid #245b91}'
        '.notice{background:#fff4e5;border-left:4px solid #9b6b28;padding:15px}'
        '.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}'
        'article,section.box{background:white;border:1px solid #dce4ee;'
        'padding:18px;border-radius:8px}table{border-collapse:collapse;width:100%}'
        'td,th{padding:9px;border-bottom:1px solid #dde5ef;text-align:left}'
        'code{overflow-wrap:anywhere}a{color:#155da5}'
        '@media(max-width:700px){.grid{grid-template-columns:1fr}}'
        '@media print{article{break-inside:avoid}body{background:white}}'
    )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta http-equiv="Content-Security-Policy" '
        'content="default-src &#39;none&#39;;style-src &#39;unsafe-inline&#39;;'
        'connect-src &#39;none&#39;;form-action &#39;none&#39;;base-uri &#39;none&#39;">'
        '<title>SRP | AeroCIE Internal Demonstration</title><style>' + css
        + '</style></head><body><header><p><strong>STRATEGICRISK PARTNERS | AeroCIE</strong></p>'
        '<h1>Source-linked regulatory intelligence</h1>'
        '<p>Offline prototype | Synthetic research case | As-of '
        + e(data["as_of"]) + '</p></header>'
        '<p class="notice"><strong>INTERNAL DEMO ONLY — NOT AUTHORIZED FOR CLIENT RELEASE.</strong>'
        ' Local fingerprints are not government signatures. No FAA approval, legal '
        'applicability, compliance, operative date, or complete regulatory history '
        'is established.</p><section class="box"><h2>' + e(data["subject"])
        + '</h2><p>Research hypothesis: ' + e(data["rationale"]) + '</p>'
        '<p><strong>Locally checked research steps: ' + str(completed)
        + ' | Unresolved: ' + str(unresolved) + '.</strong></p></section>'
        '<h2>Published metadata and source links</h2><div class="grid">'
        + ''.join(docs) + '</div>'
        '<section class="box"><h2>Proposed correction lineage</h2><ul>'
        + (edges or '<li>No linked correction found locally</li>')
        + '</ul></section><section class="box"><h2>Human review checklist</h2>'
        '<p>Reviewer names, private notes and self-attestation contents are omitted.</p>'
        '<table><thead><tr><th>Check</th><th>Instruction</th><th>Status</th></tr>'
        '</thead><tbody>' + rows + '</tbody></table></section>'
        '<footer><p>Packet hash (local only): <code>' + e(data["packet_hash"])
        + '</code></p><p>HOLD_FOR_HUMAN_REVIEW | NOT_DETERMINED | '
        'EXTERNAL RELEASE NOT AUTHORIZED</p></footer></body></html>'
    )


def write_demo(packet_path: Path, journal_path: Path | None, output: Path) -> dict:
    data = build_preview(packet_path, journal_path)
    if (output.suffix.lower() != ".html" or output.resolve() == packet_path.resolve()
            or (journal_path is not None and output.resolve() == journal_path.resolve())):
        raise ValueError("Output must be a separate HTML file")
    if output.exists():
        raise FileExistsError("Refusing to overwrite an existing demo")
    body = render_html(data)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as f:
        f.write(body)
    return {"out_html": str(output), "review_disposition": "HOLD_FOR_HUMAN_REVIEW",
            "external_release_authorized": False, "compliance_status": "NOT_DETERMINED"}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="AeroCIE synthetic-only offline demo")
    p.add_argument("--packet", type=Path, required=True)
    p.add_argument("--journal", type=Path)
    p.add_argument("--out-html", type=Path, required=True)
    a = p.parse_args(argv)
    try:
        result = write_demo(a.packet, a.journal, a.out_html)
    except (ValueError, TypeError, KeyError, OSError, json.JSONDecodeError) as exc:
        print("Demo generation refused:", exc, file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
