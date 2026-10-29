"""Phase 20 preparation: offline synthetic intake and source-linked draft reports."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from . import demo_brief
from .review_journal import _packet

SCHEMA = "AEROCIE-PHASE20-SYNTHETIC-INTAKE-v1"
FIELDS = {"schema", "synthetic", "case_id", "subject_id", "organization", "requested_scope"}


def validate_intake(value: object) -> dict:
    if not isinstance(value, dict) or set(value) != FIELDS:
        raise ValueError("Intake must contain exactly the documented fields; no contact or private data")
    if value["schema"] != SCHEMA or value["synthetic"] is not True:
        raise ValueError("Only explicitly synthetic intake is supported")
    for key in ("case_id", "subject_id"):
        if not isinstance(value[key], str) or not re.fullmatch(r"demo:[a-zA-Z0-9:_-]{1,100}", value[key]):
            raise ValueError(f"{key} must be a bounded demo: identifier")
    for key in ("organization", "requested_scope"):
        if not isinstance(value[key], str) or not value[key].strip() or len(value[key]) > 1000:
            raise ValueError(f"Invalid {key}")
    if not value["organization"].startswith("Synthetic "):
        raise ValueError("Organization must begin with Synthetic")
    return dict(value)


def build_report(intake_path: Path, packet_path: Path, journal_path: Path | None = None) -> dict:
    intake = validate_intake(json.loads(intake_path.read_text(encoding="utf-8-sig")))
    packet = _packet(packet_path)
    if packet["research_candidate"]["subject_id"] != intake["subject_id"]:
        raise ValueError("Intake subject does not match the evidence packet")
    preview = demo_brief.build_preview(packet_path, journal_path)
    # Synthetic fixtures contain intentionally fictional document numbers and URLs.
    # Never present those placeholder URLs as live official-source hyperlinks.
    for publication in preview["documents"]:
        if publication.get("local_state") == "SYNTHETIC_FIXTURE_NOT_VERIFIED":
            publication["url"] = None
    return {
        "schema": "AEROCIE-PHASE20-INTERNAL-REPORT-v1",
        "intake": intake,
        "intake_sha256": hashlib.sha256(intake_path.read_bytes()).hexdigest(),
        "evidence": preview,
        "source_link_status": "FORMAT_CHECKED_ONLY_NOT_FETCHED_OR_VERIFIED",
        "limitations": [
            "Synthetic workflow demonstration, not customer delivery.",
            "No applicability, compliance or legal conclusion is generated.",
            "Source links and local hashes do not establish source authenticity or current authority.",
            "Synthetic labels are declarations, not a personal-data detection system.",
        ],
        "external_release_authorized": False,
    }


def render_report(report: dict) -> str:
    intake = validate_intake(report["intake"])
    if report.get("external_release_authorized") is not False:
        raise ValueError("External release is not supported")
    e = demo_brief.e
    section = ('<section class="box"><h2>Customer intake workflow | Synthetic sample</h2>'
               '<p>Case: ' + e(intake["case_id"]) + '</p><p>Organization: '
               + e(intake["organization"]) + '</p><p>Requested research scope: '
               + e(intake["requested_scope"]) + '</p><p>Intake SHA-256: <code>'
               + e(report["intake_sha256"]) + '</code></p><p>Source links: '
               + e(report["source_link_status"]) + '</p><ul>'
               + ''.join('<li>' + e(item) + '</li>' for item in report["limitations"])
               + '</ul></section>')
    # Insert intake notes at the start of the document body, after the header.
    return demo_brief.render_html(report["evidence"]).replace('</header>', '</header>' + section, 1)


def write_report(intake: Path, packet: Path, journal: Path | None, output: Path) -> dict:
    report = build_report(intake, packet, journal)
    html = render_report(report)
    # Claim a new directory exclusively. Existing files and input databases are never opened for writing.
    output.mkdir(parents=True, exist_ok=False)
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (output / "report.html").write_text(html, encoding="utf-8")
    return {"output_directory": str(output), "external_release_authorized": False}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--intake", required=True, type=Path)
    parser.add_argument("--packet", required=True, type=Path)
    parser.add_argument("--journal", type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = write_report(args.intake, args.packet, args.journal, args.out_dir)
    except (ValueError, TypeError, KeyError, OSError) as exc:
        print("Report generation refused:", exc, file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
