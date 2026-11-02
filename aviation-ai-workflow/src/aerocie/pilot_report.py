"""AeroCIE-017: print-ready, synthetic-only, internal research report.

This is a report-design exercise, not a source verification, compliance
certification, customer deliverable, or external-release authorization.
"""
from __future__ import annotations

import argparse
from html import escape
import hashlib
import json
from pathlib import Path
import sys

from . import customer_report, demo_brief
from .audit_packet import CHECKS

SCHEMA = "AEROCIE-017-INTERNAL-PILOT-PREVIEW-v1"


def _e(value: object) -> str:
    return escape("" if value is None else str(value), quote=True)


def _link(url: object) -> str:
    # Link allowlist is deliberately narrow. A syntactically plausible link is
    # not proof that the source exists or is authoritative.
    safe = demo_brief._official_url(url)
    if safe is None:
        return '<span class="missing">Not available / not verified</span>'
    return ('<a target="_blank" rel="noopener noreferrer" '
            'referrerpolicy="no-referrer" href="' + _e(safe) + '">'
            'Open published source</a>')


def make_model(intake: Path, packet: Path, journal: Path | None = None) -> dict:
    report = customer_report.build_report(intake, packet, journal)
    candidate = report["evidence"]
    if (report["external_release_authorized"] is not False
            or candidate["external_release_authorized"] is not False
            or candidate["applicability_status"] != "NOT_DETERMINED"
            or candidate["compliance_status"] != "NOT_DETERMINED"
            or candidate["review_disposition"] != "HOLD_FOR_HUMAN_REVIEW"):
        raise ValueError("Only held, undetermined, synthetic research may be presented")

    states = candidate["checks"]
    if (len(states) != len(CHECKS)
            or [c["id"] for c in states] != [item[0] for item in CHECKS]
            or any(c["state"] not in demo_brief.STATES for c in states)):
        raise ValueError("Unexpected or corrupted review checklist")
    checked = sum(c["state"] == "CHECKED_RESEARCH_ONLY" for c in states)
    documents = candidate["documents"]
    if not documents:
        raise ValueError("At least one research document is required")
    if any(not isinstance(d, dict) for d in documents):
        raise ValueError("Invalid publication list")
    return {
        "schema": SCHEMA,
        "internal_only": True,
        "intake": report["intake"],
        "intake_sha256": report["intake_sha256"],
        "subject": candidate["subject"],
        "research_hypothesis": candidate["rationale"],
        "as_of": candidate["as_of"],
        "packet_sha256": candidate["packet_hash"],
        "documents": documents,
        "corrections": candidate["corrections"],
        "checks": states,
        "counts": {
            "documents": len(documents),
            "proposed_correction_links": len(candidate["corrections"]),
            "recorded_research_checks": checked,
            "unresolved_review_checks": len(states) - checked,
        },
        "release_status": "HOLD_FOR_HUMAN_REVIEW",
        "applicability_status": "NOT_DETERMINED",
        "compliance_status": "NOT_DETERMINED",
        "source_link_status": report["source_link_status"],
        "external_release_authorized": False,
        "limits": (
            "Synthetic internal prototype. Publications and correction edges are "
            "research candidates; URLs are checked for format only, not fetched "
            "or verified in this report. Local hashes do not authenticate FAA "
            "authority. No live regulatory search, legally operative status, "
            "facility-specific applicability, insurance coverage analysis, "
            "compliance certification, or authorization for customer release."
        ),
    }


def render_html(model: dict) -> str:
    if (model.get("schema") != SCHEMA or model.get("internal_only") is not True
            or model.get("external_release_authorized") is not False
            or model.get("release_status") != "HOLD_FOR_HUMAN_REVIEW"
            or model.get("applicability_status") != "NOT_DETERMINED"
            or model.get("compliance_status") != "NOT_DETERMINED"):
        raise ValueError("Invalid pilot report release guard")
    checks = model["checks"]
    if (len(checks) != len(CHECKS)
            or [item["id"] for item in checks] != [check[0] for check in CHECKS]
            or any(item["state"] not in demo_brief.STATES for item in checks)):
        raise ValueError("Invalid human-review states")
    if model["counts"]["unresolved_review_checks"] != sum(
            item["state"] != "CHECKED_RESEARCH_ONLY" for item in checks):
        raise ValueError("Review state count mismatch")
    intake = customer_report.validate_intake(model["intake"])
    if not isinstance(model["documents"], list) or not model["documents"]:
        raise ValueError("Missing evidence documents")

    docs = []
    chronology = []
    for doc in model["documents"]:
        # A source marked synthetic cannot become an apparently authentic link
        # even if the preview model was modified by a caller.
        url = None if doc.get("local_state") == "SYNTHETIC_FIXTURE_NOT_VERIFIED" else doc.get("url")
        docs.append(
            '<tr><td><strong>' + _e(doc.get("number")) + '</strong><span class="subline">'
            + _e(doc.get("title")) + '</span></td><td>' + _e(doc.get("published"))
            + '</td><td>' + _e(doc.get("local_state"))
            + '</td><td>' + _link(url) + '</td></tr>'
        )
        chronology.append(
            '<li><span class="date">' + _e(doc.get("published"))
            + '</span><span><strong>' + _e(doc.get("number"))
            + '</strong> — publication metadata recorded. Stated effective: '
            + _e(doc.get("effective") or "Not established")
            + '. This is not a verified legal-effective-date finding.</span></li>'
        )
    relations = ''.join(
        '<tr><td>' + _e(edge.get("from")) + '</td><td>CORRECTS (proposed research association)</td>'
        '<td>' + _e(edge.get("to")) + '</td><td>' + _e(edge.get("state")) + '</td></tr>'
        for edge in model["corrections"]
    ) or '<tr><td colspan="4">No correction relationships indexed in this local sample; coverage is not established.</td></tr>'
    check_rows = ''.join(
        '<tr><td><strong>' + _e(c["id"]) + '</strong></td><td>'
        + _e(c["instruction"]) + '</td><td><span class="status">'
        + _e(c["state"]) + '</span></td></tr>'
        for c in checks
    )
    stats = [
        ("SOURCE RECORDS", model["counts"]["documents"]),
        ("CORRECTION CANDIDATES", model["counts"]["proposed_correction_links"]),
        ("CHECKS RECORDED", model["counts"]["recorded_research_checks"]),
        ("REVIEWS UNRESOLVED", model["counts"]["unresolved_review_checks"]),
    ]
    metrics = ''.join('<div class="stat"><strong>' + _e(v)
                      + '</strong><span>' + _e(k) + '</span></div>' for k, v in stats)
    css = """
    @page {size: Letter; margin: 0.51in 0.56in;}
    :root{font-family:Montserrat,Arial,sans-serif;color:#142e4a;background:#f2f5f8}
    *{box-sizing:border-box}body{margin:0}main{max-width:1110px;margin:auto;padding:28px 36px}
    h1{font-size:34px;letter-spacing:-.9px;line-height:1.13;margin:14px 0}
    h2{font-size:19px;letter-spacing:-.25px;margin:0 0 14px}
    h3{font-size:14px;margin:0 0 9px}
    p,td{line-height:1.5}.muted{color:#526a83}.lead{font-size:15px;max-width:780px}
    .banner{background:#0a2444;color:#fff;padding:35px max(36px,calc((100vw - 1038px)/2));border-bottom:7px solid #2b72b5}
    .banner .brand{font-size:13px;font-weight:750;letter-spacing:1.4px}
    .banner .sub{color:#c0d6ee}.banner .micro{font-size:11px;color:#acc6e1}
    .restriction{margin:0 0 22px;background:#fff3e4;border-left:4px solid #b87926;padding:13px 16px;font-size:12px;line-height:1.55}
    .stats{display:grid;grid-template-columns:repeat(4,1fr);gap:11px;margin:24px 0}
    .stat{border:1px solid #d7e2ec;background:#fff;border-radius:8px;padding:15px}
    .stat strong{display:block;color:#154e82;font-size:29px;line-height:1.1}
    .stat span{font-size:10px;letter-spacing:.4px;color:#536d86;font-weight:bold}
    section.sheet{background:#fff;border:1px solid #dce4eb;padding:24px;border-radius:9px;margin:20px 0}
    .two{display:grid;grid-template-columns:1.12fr 1fr;gap:17px}
    .eyebrow{font-size:10px;color:#2d6ba4;font-weight:750;letter-spacing:1.1px}
    .finding{border-left:3px solid #2b72b5;background:#f3f7fc;padding:10px 13px;margin:10px 0}
    .finding strong{display:block;font-size:12px}.finding span{display:block;color:#4b6076;font-size:12px}
    table{border-collapse:collapse;width:100%;font-size:11px;table-layout:fixed}
    td,th{border-bottom:1px solid #e0e7ed;text-align:left;padding:11px 8px;vertical-align:top;overflow-wrap:anywhere}
    th{background:#edf3f8;color:#2a4b6c;font-size:10px;text-transform:uppercase;letter-spacing:.3px}
    .subline{display:block;color:#587087;font-size:10px;margin-top:5px}
    .status{color:#7c511f;font-weight:bold;font-size:10px}.missing{color:#7b4a20}
    .steps{list-style:none;padding:0;margin:0}.steps li{display:grid;grid-template-columns:118px 1fr;gap:12px;padding:12px 0;border-bottom:1px solid #e2e8ef;font-size:12px}
    .date{color:#25649c;font-weight:750}.foot{font-size:10px;color:#5b6f85;word-break:break-word}
    .signoff{margin-top:14px;border:1px solid #c7d5e2;border-radius:5px;padding:15px;background:#f8fafc;color:#4c6175;font-size:12px}
    a{color:#155c98}code{word-break:break-all;font-size:10px}
    @media(max-width:760px){main{padding:18px}.stats{grid-template-columns:repeat(2,1fr)}.two{grid-template-columns:1fr}.banner{padding:30px 18px}}
    @media print{ :root{background:#fff} .banner{background:#0a2444!important;-webkit-print-color-adjust:exact;print-color-adjust:exact}
    main{padding:0}section.sheet{break-inside:avoid;border:1px solid #dce4eb;margin:10px 0;padding:16px}td,th{padding:7px 6px}p,td{line-height:1.34}h2{margin-bottom:9px}.signoff{padding:10px}
    .restriction,.stat{break-inside:avoid}tr{break-inside:avoid}
    .page-break{break-before:page}a{text-decoration:none}}
    """
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta http-equiv="Content-Security-Policy" content="default-src &#39;none&#39;; '
        'style-src &#39;unsafe-inline&#39;; img-src &#39;none&#39;; connect-src &#39;none&#39;; '
        'form-action &#39;none&#39;; base-uri &#39;none&#39;">'
        '<title>StrategicRisk Partners | Aviation Research Preview</title><style>' + css + '</style></head><body>'
        '<header class="banner"><div class="brand">STRATEGICRISK PARTNERS <span style="color:#8dbbe5">|</span> AeroCIE</div>'
        '<h1>Aviation Regulatory<br>Intelligence Review</h1>'
        '<p class="sub lead">Research brief design preview | Synthetic demonstration subject</p>'
        '<p class="micro">INTERNAL DRAFT | PROPOSED $995 FIXED-SCOPE OFFER | NOT A CLIENT DELIVERABLE</p></header><main>'
        '<div class="restriction"><strong>DEMONSTRATION ONLY — NOT FOR CLIENT RELEASE.</strong> '
        'No FAA approval, legal determination or compliance certification. '
        'Document identifiers and citations may be fictional fixtures. '
        'The report has not established completeness or current legal authority.</div>'
        '<section class="sheet"><span class="eyebrow">ENGAGEMENT SNAPSHOT</span><h2>'
        + _e(model["subject"]) + '</h2><div class="two"><div>'
        '<p><strong>Organization</strong><br>' + _e(intake["organization"])
        + '</p><p><strong>Internal case</strong><br>' + _e(intake["case_id"])
        + '</p><p><strong>Requested research scope</strong><br>' + _e(intake["requested_scope"])
        + '</p></div><div><div class="finding"><strong>Research posture</strong><span>'
        'HOLD FOR HUMAN REVIEW</span></div><div class="finding"><strong>Legal applicability</strong>'
        '<span>NOT DETERMINED</span></div><div class="finding"><strong>Source authority</strong><span>'
        'Local snapshot and format checks only</span></div></div></div></section>'
        '<section class="stats" aria-label="Key research quantities">' + metrics + '</section>'
        '<section class="sheet"><span class="eyebrow">01 | EXECUTIVE SUMMARY</span>'
        '<h2>What the research workflow establishes</h2>'
        '<p>For this synthetic case, AeroCIE has assembled locally recorded publication metadata, '
        'proposed correction associations and review status. Those are demonstrations of the '
        'research process, <strong>not verified findings of a regulatory obligation.</strong></p>'
        '<p><strong>Research question:</strong> ' + _e(model["research_hypothesis"])
        + '</p><p><strong>Evidence snapshot date:</strong> ' + _e(model["as_of"])
        + '</p><p><strong>Still required:</strong> independent source inspection, subsequent-change '
        'search, subject-fact validation, operative-date analysis and qualified review as applicable.</p></section>'
        '<section class="sheet"><span class="eyebrow">02 | EVIDENCE REGISTER</span>'
        '<h2>Publications and source links</h2>'
        '<p class="muted">Links are allowlisted by hostname, not authenticated or fetched. '
        'Fictional sources are explicitly not clickable.</p><table><thead><tr>'
        '<th style="width:34%">Reference</th><th style="width:16%">Published</th>'
        '<th style="width:30%">Local evidence status</th><th style="width:20%">Source</th>'
        '</tr></thead><tbody>' + ''.join(docs) + '</tbody></table></section>'
        '<section class="sheet"><span class="eyebrow">03 | TIMELINE & CHANGES</span>'
        '<h2>Publication chronology</h2><ol class="steps">' + ''.join(chronology) + '</ol>'
        '<h3 style="margin-top:20px">Proposed document relationships</h3>'
        '<table><thead><tr><th>Later record</th><th>Proposed relationship</th>'
        '<th>Earlier record</th><th>Evidence state</th></tr></thead><tbody>'
        + relations + '</tbody></table></section>'
        '<section class="sheet"><span class="eyebrow">04 | CONTROLLED REVIEW</span>'
        '<h2>Human verification checklist</h2><p class="muted">A recorded research step '
        'does not establish certification or release approval. Individual reviewer notes are excluded.</p>'
        '<table><thead><tr><th style="width:22%">Item</th><th>Required verification</th>'
        '<th style="width:25%">Current state</th></tr></thead><tbody>'
        + check_rows + '</tbody></table></section>'
        '<section class="sheet"><span class="eyebrow">05 | METHODOLOGY & LIMITS</span>'
        '<h2>Interpretation and release conditions</h2>'
        '<p>' + _e(model["limits"]) + '</p><p><strong>Source verification:</strong> '
        + _e(model["source_link_status"]) + '</p>'
        '<div class="signoff"><strong>Internal release gates — ALL OPEN</strong><p>'
        '☐ Independent current-source verification &nbsp;&nbsp; ☐ Relevant facility or aircraft facts<br>'
        '☐ Subject-specific analysis &nbsp;&nbsp; ☐ Privacy/security review<br>'
        '☐ Report editorial approval &nbsp;&nbsp; ☐ Explicit external-release authorization</p>'
        'No signature or approval is implied by this checklist.</div></section>'
        '<p class="foot"><strong>Audit anchors:</strong> intake SHA-256: <code>'
        + _e(model["intake_sha256"]) + '</code><br>Packet SHA-256: <code>'
        + _e(model["packet_sha256"]) + '</code></p>'
        '</main></body></html>'
    )


def write_preview(intake: Path, packet: Path, journal: Path | None, output: Path) -> dict:
    model = make_model(intake, packet, journal)
    html = render_html(model)
    if output.resolve() in {intake.resolve(), packet.resolve(), *( [journal.resolve()] if journal is not None else [] )}:
        raise ValueError("Refusing to overwrite any research input")
    if output.suffix.lower() != ".html":
        raise ValueError("Output must be HTML")
    if output.exists():
        raise FileExistsError("Preview already exists; refusing to overwrite")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as f:
        f.write(html)
    return {"html_path": str(output), "external_release_authorized": False,
            "research_status": "HOLD_FOR_HUMAN_REVIEW", "source_count": model["counts"]["documents"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Phase 21 offline internal pilot report design preview")
    parser.add_argument("--intake", type=Path, required=True)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--journal", type=Path)
    parser.add_argument("--out-html", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = write_preview(args.intake, args.packet, args.journal, args.out_html)
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print("Phase 21 preview refused:", exc, file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
