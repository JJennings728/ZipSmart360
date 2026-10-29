"""Retrospective pilot evaluation of AeroCIE underwriting research labels.

Never treats a triage classification as a binding insurance decision. Metrics
measure classification agreement and flagged adverse outcomes, not causality,
avoided losses, actuarial accuracy, or an insurability determination.
"""
from __future__ import annotations

import argparse
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

SCHEMA = "AEROCIE-PILOT-EVALUATION-v1"
LABELS = frozenset({"Quote", "Refer", "Decline"})
REQUIRED_FIELDS = frozenset({"case_id", "aerocie_label", "baseline_label", "adverse_outcome", "baseline_minutes", "aerocie_minutes"})
OPTIONAL_FIELDS = frozenset({"evidence_complete"})


def _decimal(value: Any, field: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float, str, Decimal)):
        raise ValueError(f"{field} must be a finite nonnegative numeric value")
    try:
        val = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError(f"Invalid {field}") from exc
    if not val.is_finite() or val < 0 or val > 10000:
        raise ValueError(f"{field} outside accepted range")
    return val


def _ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def _metrics(cases: list[dict], label_field: str) -> dict:
    """Flagged means Refer/Decline; adverse outcome is historical outcome field."""
    labelled = [c for c in cases if c["adverse_outcome"] is not None]
    tp = sum(c[label_field] != "Quote" and c["adverse_outcome"] for c in labelled)
    fp = sum(c[label_field] != "Quote" and not c["adverse_outcome"] for c in labelled)
    fn = sum(c[label_field] == "Quote" and c["adverse_outcome"] for c in labelled)
    tn = sum(c[label_field] == "Quote" and not c["adverse_outcome"] for c in labelled)
    return {
        "known_outcome_cases": len(labelled),
        "true_positive": tp, "false_positive": fp, "false_negative": fn, "true_negative": tn,
        "adverse_case_recall": _ratio(tp, tp + fn),
        "positive_predictive_value": _ratio(tp, tp + fp),
        "specificity": _ratio(tn, tn + fp),
        "referrals_or_decline_review": sum(c[label_field] != "Quote" for c in cases),
        "quoted_cases": sum(c[label_field] == "Quote" for c in cases),
    }


def evaluate(document: dict, *, require_synthetic: bool = True) -> dict:
    if not isinstance(document, dict) or set(document) != {"schema", "synthetic", "case_definition", "cases"}:
        raise ValueError("Evaluation document has incorrect fields")
    if document["schema"] != SCHEMA or type(document["synthetic"]) is not bool:
        raise ValueError("Incorrect schema or synthetic flag")
    if require_synthetic and document["synthetic"] is not True:
        raise ValueError("Offline demonstration accepts synthetic outcomes only")
    definition = document["case_definition"]
    if not isinstance(definition, str) or not 12 <= len(definition.strip()) <= 300:
        raise ValueError("Specify the adverse outcome and measurement window")
    cases = document["cases"]
    if not isinstance(cases, list) or not 1 <= len(cases) <= 5000:
        raise ValueError("Expected 1 to 5000 cases")
    seen: set[str] = set()
    normalized: list[dict] = []
    for case in cases:
        if not isinstance(case, dict) or not REQUIRED_FIELDS <= set(case) or set(case) - (REQUIRED_FIELDS | OPTIONAL_FIELDS):
            raise ValueError("A case has missing or unexpected fields")
        id_ = case["case_id"]
        if not isinstance(id_, str) or not id_.startswith("demo:") or len(id_) > 80 or id_ in seen:
            raise ValueError("Each case ID must be a unique demo: identifier")
        seen.add(id_)
        if case["aerocie_label"] not in LABELS or case["baseline_label"] not in LABELS:
            raise ValueError("Invalid triage label")
        outcome = case["adverse_outcome"]
        if outcome is not None and type(outcome) is not bool:
            raise ValueError("adverse_outcome must be boolean or null")
        complete = case.get("evidence_complete", True)
        if type(complete) is not bool:
            raise ValueError("evidence_complete must be boolean")
        if not complete and case["aerocie_label"] != "Refer":
            raise ValueError("Incomplete evidence requires an AeroCIE Refer label")
        baseline_time = _decimal(case["baseline_minutes"], "baseline_minutes")
        aerocie_time = _decimal(case["aerocie_minutes"], "aerocie_minutes")
        normalized.append({"case_id": id_, "aerocie_label":case["aerocie_label"],
                           "baseline_label":case["baseline_label"], "adverse_outcome":outcome,
                           "baseline_minutes": baseline_time, "aerocie_minutes":aerocie_time,
                           "evidence_complete":complete})
    b_total = sum((x["baseline_minutes"] for x in normalized), Decimal("0"))
    a_total = sum((x["aerocie_minutes"] for x in normalized), Decimal("0"))
    denominator = Decimal(len(normalized))
    sha = hashlib.sha256(json.dumps(document, sort_keys=True, separators=(",", ":"),ensure_ascii=False).encode("utf-8")).hexdigest()
    return {
        "schema": "AEROCIE-PILOT-EVALUATION-RESULT-v1", "synthetic":document["synthetic"],
        "cases":len(normalized), "defined_adverse_outcome":definition,
        "known_outcome_cases":sum(c["adverse_outcome"] is not None for c in normalized),
        "unknown_outcome_cases":sum(c["adverse_outcome"] is None for c in normalized),
        "missing_evidence_cases":sum(not c["evidence_complete"] for c in normalized),
        "aerocie":_metrics(normalized, "aerocie_label"),
        "baseline":_metrics(normalized, "baseline_label"),
        "avg_baseline_minutes":float(round(b_total/denominator,2)),
        "avg_aerocie_minutes":float(round(a_total/denominator,2)),
        "total_minutes_saved":float(round(b_total-a_total,2)),
        "time_reduction_ratio":float(round((b_total-a_total)/b_total,4)) if b_total else None,
        "data_sha256":sha,
        "interpretation":"Retrospective association and process timing only. Not prospective loss prediction, prevented claims, or pricing adequacy.",
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args=p.parse_args(argv)
    try:
        if args.out.resolve() == args.input.resolve() or args.out.exists() or args.out.suffix.lower() != ".json":
            raise ValueError("Output must be a new JSON path")
        document=json.loads(args.input.read_text(encoding="utf-8-sig"))
        result=evaluate(document)
        args.out.parent.mkdir(parents=True,exist_ok=True)
        with args.out.open("x",encoding="utf-8") as stream:
            json.dump(result,stream,indent=2)
            stream.write("\n")
        print(json.dumps({"output":str(args.out),"cases":result["cases"],"synthetic":True}))
        return 0
    except (ValueError, KeyError, OSError, TypeError, json.JSONDecodeError) as exc:
        print(f"AeroCIE pilot evaluation refused: {exc}",file=sys.stderr)
        return 1


if __name__=="__main__":
    raise SystemExit(main())
