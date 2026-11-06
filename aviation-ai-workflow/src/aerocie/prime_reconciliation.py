"""AeroCIE-031 | deterministic, offline synthetic SCRM reconciliation and review packet.

This module is a research-quality demonstration, not an external audit, verified
supplier traceability, cybersecurity authorization, or program schedule forecast.
It uses the existing JSON/CSV adapters and prime_pilot model without altering them.
"""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any

from .prime_adapters import load_csv_bundle, load_json
from .prime_pilot import SCHEMA, digest, evaluate

PACKET_SCHEMA = "SRP-SCRM-REVIEW-PACKET-v1"
SOURCE_SECTIONS = (("evidence", "evidence_id"),
                   ("suppliers", "supplier_id"),
                   ("components", "component_id"))


def _load(adapter: str, source: Path) -> dict[str, Any]:
    if adapter == "json":
        return load_json(source)
    if adapter == "csv":
        return load_csv_bundle(source)
    raise ValueError("Adapter must be json or csv")


def _index(payload: dict, section: str, key: str) -> dict[str, dict]:
    # evaluate() must be called before indexing, to reject malformed references.
    return {row[key]: row for row in payload[section]}


def _check_report(payload: dict, report: dict) -> None:
    """Independently reconcile model totals and its computed report fingerprint."""
    if report["schema"] != SCHEMA or report["input_sha256"] != digest(payload):
        raise ValueError("Input-to-report fingerprint reconciliation failed")
    if report["report_sha256"] != digest({
        key: value for key, value in report.items() if key != "report_sha256"
    }):
        raise ValueError("Model report fingerprint reconciliation failed")

    components = report["components"]
    summary = report["summary"]
    expected_flags = sum(item["review_flag"] for item in components)
    expected_single = sum(item["single_source_assumed"] for item in components)
    critical = [item["lead_time_increase_days"] for item in components
                if item["critical_path_assumed"]]
    expected_critical = max(critical, default=None)
    checks = (
        (summary["components_evaluated"], len(payload["components"])),
        (summary["supplier_count"], len(payload["suppliers"])),
        (summary["review_flag_count"], expected_flags),
        (summary["single_source_assumptions"], expected_single),
        (summary["largest_assumed_critical_component_increase_days"], expected_critical),
    )
    if any(actual != expected for actual, expected in checks):
        raise ValueError("Model summary failed independent reconciliation")
    if summary["schedule_forecast"] != "NOT_AVAILABLE_NO_VALIDATED_DEPENDENCY_NETWORK":
        raise ValueError("Unvalidated program schedule forecast detected")
    if report["external_release_authorized"] is not False or report["status"] != "INTERNAL_SYNTHETIC_ONLY":
        raise ValueError("Unsafe report release status")


def _snapshot(payload: dict) -> dict:
    report = evaluate(payload)
    _check_report(payload, report)
    row_fingerprints = {
        section: {key: digest(row) for key, row in
                  sorted(_index(payload, section, id_field).items())}
        for section, id_field in SOURCE_SECTIONS
    }
    evidence = _index(payload, "evidence", "evidence_id")
    used_evidence = {row["evidence_id"] for row in payload["components"]}
    used_suppliers = {row["supplier_id"] for row in payload["components"]}
    supplier_ids = set(row_fingerprints["suppliers"])
    evidence_ids = set(row_fingerprints["evidence"])
    findings = [
        {"code": "UNREFERENCED_SUPPLIER", "record_id": supplier_id, "disposition": "REVIEW_REQUIRED"}
        for supplier_id in sorted(supplier_ids - used_suppliers)
    ] + [
        {"code": "UNREFERENCED_EVIDENCE", "record_id": evidence_id, "disposition": "REVIEW_REQUIRED"}
        for evidence_id in sorted(evidence_ids - used_evidence)
    ]
    queue = []
    for item in report["components"]:
        if not item["review_flag"]:
            continue
        source = evidence[item["evidence_id"]]
        queue.append({
            "component_id": item["component_id"],
            "supplier_id": item["supplier_id"],
            "evidence_id": item["evidence_id"],
            "evidence_sha256": source["sha256"],
            "component_record_sha256": row_fingerprints["components"][item["component_id"]],
            "lead_time_increase_days": item["lead_time_increase_days"],
            "single_source_assumed": item["single_source_assumed"],
            "critical_path_assumed": item["critical_path_assumed"],
            "review_reason_codes": (["SINGLE_SOURCE_ASSUMED"] if item["single_source_assumed"] else [])
                + (["LEAD_TIME_INCREASE"] if item["lead_time_increase_days"] > 0 else []),
            "human_disposition": "OPEN_NOT_REVIEWED",
            "evidence_status": "LOCAL_FINGERPRINT_ONLY_NOT_SOURCE_AUTHENTICATION",
        })
    return {
        "input_sha256": report["input_sha256"],
        "model_report_sha256": report["report_sha256"],
        "record_sha256": row_fingerprints,
        "source_counts": {section: len(row_fingerprints[section]) for section, _ in SOURCE_SECTIONS},
        "findings": findings,
        "review_queue": queue,
        "model_summary": summary_copy(report["summary"]),
        "program": payload["program"],
    }


def summary_copy(summary: dict) -> dict:
    """Do not alias the underlying model object into the public packet."""
    return {key: summary[key] for key in sorted(summary)}


def _delta(before: dict, after: dict) -> dict:
    changes: dict[str, dict] = {}
    for section, _ in SOURCE_SECTIONS:
        left = before["record_sha256"][section]
        right = after["record_sha256"][section]
        changes[section] = {
            "added_ids": sorted(right.keys() - left.keys()),
            "removed_ids": sorted(left.keys() - right.keys()),
            "modified_ids": sorted(key for key in left.keys() & right.keys()
                                   if left[key] != right[key]),
        }
    changes["changed"] = any(
        changes[section][label]
        for section, _ in SOURCE_SECTIONS
        for label in ("added_ids", "removed_ids", "modified_ids")
    )
    return changes


def build_packet(adapter: str, source: Path, *,
                 baseline_adapter: str | None = None,
                 baseline_source: Path | None = None) -> dict:
    """Produce a reproducible audit-*preparation* packet, never an audit conclusion."""
    if (baseline_adapter is None) != (baseline_source is None):
        raise ValueError("Baseline adapter and source must be provided together")
    latest = _snapshot(_load(adapter, source))
    base = (_snapshot(_load(baseline_adapter, baseline_source))
            if baseline_adapter is not None and baseline_source is not None else None)
    if base and latest["program"] != base["program"]:
        raise ValueError("Cannot reconcile different program labels")
    diff = _delta(base, latest) if base else None
    packet = {
        "schema": PACKET_SCHEMA,
        "program": latest["program"],
        "classification": "PUBLIC_SYNTHETIC_ONLY",
        "release_authorized": False,
        "decision_status": "HUMAN_REVIEW_REQUIRED",
        "verification_status": "LOCAL_INTEGRITY_AND_MODEL_RECONCILIATION_ONLY",
        "source_adapter": adapter,
        "source_input_sha256": latest["input_sha256"],
        "model_report_sha256": latest["model_report_sha256"],
        "source_counts": latest["source_counts"],
        "source_record_sha256": latest["record_sha256"],
        "model_summary": latest["model_summary"],
        "open_review_items": latest["review_queue"],
        "data_quality_findings": latest["findings"],
        "baseline_input_sha256": base["input_sha256"] if base else None,
        "source_changes_since_baseline": diff,
        "reviewer_name": None,
        "reviewer_disposition": "NOT_RECORDED",
        "limitations": [
            "Demonstration uses synthetic, self-declared inputs only.",
            "SHA-256 detects changes; it does not authenticate the actual supplier or source.",
            "A changed record is not proof of a compliance obligation or program schedule slip.",
            "No live procurement records, supplier authentication, MBSE integration, or verified CUI authorization.",
            "No CMMC certification, MOSA conformity assessment, or government contract award.",
            "Review flags are research candidates, not approved decisions.",
        ],
    }
    packet["packet_sha256"] = digest(packet)
    return packet


def _safe(value: object) -> str:
    return html.escape(str(value), quote=True).replace("|", "&#124;").replace("\n", " ")


def render_markdown(packet: dict) -> str:
    """Human-readable report with no raw evidence excerpts or active HTML."""
    if packet.get("schema") != PACKET_SCHEMA:
        raise ValueError("Unsupported packet schema")
    if packet.get("packet_sha256") != digest({
        key: value for key, value in packet.items() if key != "packet_sha256"
    }):
        raise ValueError("Packet fingerprint mismatch")
    result = [
        "# AeroCIE | Synthetic supplier dependency review packet",
        "",
        f"**Program:** {_safe(packet['program'])}",
        "**Release:** Internal synthetic demonstration only; human review required.",
        "**Classification:** PUBLIC_SYNTHETIC_ONLY (declared; not independently classified)",
        "",
        "## Provenance and reconciliation",
        f"- Input SHA-256: `{packet['source_input_sha256']}`",
        f"- Model report SHA-256: `{packet['model_report_sha256']}`",
        f"- Packet SHA-256: `{packet['packet_sha256']}`",
        f"- Adapter: `{packet['source_adapter']}`",
        "",
        "## Summary",
        f"- Components evaluated: {packet['model_summary']['components_evaluated']}",
        f"- Assumed single-source components: {packet['model_summary']['single_source_assumptions']}",
        f"- Items flagged for review: {packet['model_summary']['review_flag_count']}",
        "- Program schedule forecast: NOT AVAILABLE (dependency network not validated)",
        "",
        "## Human review queue",
        "| Component | Supplier | Evidence | Lead-time increase (days) | Reason |",
        "|---|---|---|---:|---|",
    ]
    if not packet["open_review_items"]:
        result.append("| None | — | — | — | No flagged rows |")
    else:
        for row in packet["open_review_items"]:
            result.append(
                f"| {_safe(row['component_id'])} | {_safe(row['supplier_id'])}"
                f" | {_safe(row['evidence_id'])} | {row['lead_time_increase_days']}"
                f" | {_safe(', '.join(row['review_reason_codes']))} |"
            )
    if packet["data_quality_findings"]:
        result.extend(["", "## Data coverage questions"])
        for row in packet["data_quality_findings"]:
            result.append(f"- {_safe(row['code'])}: {_safe(row['record_id'])}")
    if packet["source_changes_since_baseline"] is not None:
        result.extend(["", "## Source changes against approved synthetic baseline"])
        for section, _ in SOURCE_SECTIONS:
            row = packet["source_changes_since_baseline"][section]
            result.append(
                f"- {_safe(section)}: added={len(row['added_ids'])},"
                f" removed={len(row['removed_ids'])}, modified={len(row['modified_ids'])}"
            )
    result.extend([
        "",
        "## Pending independent review",
        "- Confirm that all source records are fictitious and permitted for this demonstration.",
        "- Review evidence references and whether any source is unreferenced.",
        "- Independently recalculate lead-time sensitivities and inspect changed records.",
        "- Do not use this output to make purchasing, certification, or program decisions.",
        "",
        "## Limitations",
        *["- " + _safe(reason) for reason in packet["limitations"]],
        "",
        "Reviewer: NOT RECORDED  |  Decision: NOT RECORDED",
        "",
    ])
    return "\n".join(result)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate offline synthetic SCRM review packet")
    parser.add_argument("--adapter", choices=("json", "csv"), required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--baseline-adapter", choices=("json", "csv"))
    parser.add_argument("--baseline-source", type=Path)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--output-md", type=Path)
    args = parser.parse_args(argv)
    outputs = [path for path in (args.output_json, args.output_md) if path is not None]
    if len({path.resolve() for path in outputs}) != len(outputs):
        parser.error("Output paths must be different")
    for path in outputs:
        if path.exists() or path.is_symlink():
            parser.error(f"Refusing to replace existing output: {path}")
    try:
        packet = build_packet(args.adapter, args.source,
                              baseline_adapter=args.baseline_adapter,
                              baseline_source=args.baseline_source)
        formatted_json = json.dumps(packet, indent=2, sort_keys=True, allow_nan=False) + "\n"
        formatted_md = render_markdown(packet)
        if not outputs:
            print(formatted_json, end="")
            return 0
        for path in outputs:
            path.parent.mkdir(parents=True, exist_ok=True)
            data = formatted_json if path == args.output_json else formatted_md
            with path.open("x", encoding="utf-8") as file:
                file.write(data)
        return 0
    except (OSError, ValueError, TypeError) as exc:
        parser.exit(2, f"Review packet error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
