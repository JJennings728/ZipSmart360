"""AeroCIE Phase 23 | deterministic model evaluation and cited-output audit.

This module evaluates supplied predictions and evidence records. It does not
execute a generative model, validate actual market performance, or authorize an
underwriting or regulatory conclusion.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import re
import sys

SCHEMA = "AEROCIE-MODEL-EVAL-v1"
OUTPUT_SCHEMA = "AEROCIE-MODEL-ASSURANCE-REPORT-v1"
MIN_TEST_SET = 100
MIN_GROUP = 25
MAX_BRIER = 0.20
MAX_ECE = 0.10
MAX_GROUP_BRIER_GAP = 0.10


class InputRejected(ValueError):
    """Unsafe, ambiguous, or malformed synthetic evaluation input."""


def _digest(payload: object) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def _exact_keys(obj: object, keys: set[str], name: str) -> dict:
    if not isinstance(obj, dict) or set(obj) != keys:
        raise InputRejected(f"{name}: expected exact fields {sorted(keys)}")
    return obj


def _safe_string(value: object, name: str, limit: int = 300) -> str:
    if not isinstance(value, str) or not 0 < len(value.strip()) <= limit:
        raise InputRejected(f"Invalid {name}")
    if "\x00" in value:
        raise InputRejected(f"Invalid {name}")
    return value


def _probability(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
        raise InputRejected("Predictions must contain finite numeric probabilities")
    if not 0 <= value <= 1:
        raise InputRejected("Probability must be within 0..1")
    return float(value)


def _evaluation(rows: object) -> dict:
    if not isinstance(rows, list) or not rows or len(rows) > 100000:
        raise InputRejected("Expected 1..100000 test rows")
    seen = set()
    segments: dict[str, list[tuple[float, int]]] = defaultdict(list)
    bins: dict[int, list[tuple[float, int]]] = defaultdict(list)
    squared = []
    case_errors = []
    for row in rows:
        obj = _exact_keys(row, {"case_id", "probability", "observed", "segment"}, "row")
        case = _safe_string(obj["case_id"], "case_id", 100)
        if not case.startswith("demo:") or case in seen:
            raise InputRejected("Each test row needs a distinct demo: case ID")
        seen.add(case)
        pred = _probability(obj["probability"])
        observed = obj["observed"]
        if type(observed) is not int or observed not in (0, 1):
            raise InputRejected("Observed outcome must be integer 0 or 1")
        segment = _safe_string(obj["segment"], "segment", 80)
        if not segment.startswith("Synthetic "):
            raise InputRejected("Only synthetic segments are supported")
        segments[segment].append((pred, observed))
        bins[min(9, int(pred * 10))].append((pred, observed))
        sq_err = (pred - observed) ** 2
        squared.append(sq_err)
        case_errors.append({"case_id": case, "segment": segment,
                            "predicted_probability": pred, "observed_outcome": observed,
                            "squared_error": round(sq_err, 6)})
    brier = sum(squared) / len(rows)
    ece = sum(len(group) / len(rows) * abs(
        sum(p for p, _ in group) / len(group) - sum(y for _, y in group) / len(group)
    ) for group in bins.values())
    by_segment = {}
    for name, group in sorted(segments.items()):
        score = sum((p - y) ** 2 for p, y in group) / len(group)
        by_segment[name] = {"count": len(group), "brier": round(score, 6),
                            "statistically_reviewable": len(group) >= MIN_GROUP}
    reviewed = [v["brier"] for v in by_segment.values() if v["statistically_reviewable"]]
    spread = round(max(reviewed) - min(reviewed), 6) if len(reviewed) >= 2 else None
    return {"count": len(rows), "brier": round(brier, 6), "ece": round(ece, 6),
            "by_segment": by_segment, "segment_brier_spread": spread,
            "calibration_bins_observed": len(bins),
            "largest_observed_errors": sorted(case_errors,
                key=lambda r: (-r["squared_error"], r["case_id"]))[:5]}


def _claims(evidence: object, claims: object) -> dict:
    if not isinstance(evidence, list) or not isinstance(claims, list) or len(evidence) > 1000 or len(claims) > 1000:
        raise InputRejected("Invalid evidence or claim list")
    indexed = {}
    for item in evidence:
        obj = _exact_keys(item, {"id", "text", "text_sha256", "source_url", "human_checked"}, "evidence")
        eid = _safe_string(obj["id"], "evidence ID", 100)
        text = _safe_string(obj["text"], "evidence text", 5000)
        if eid in indexed:
            raise InputRejected("Duplicate evidence ID")
        if not isinstance(obj["human_checked"], bool):
            raise InputRejected("Evidence verification must be boolean")
        if not re.fullmatch(r"https://[a-zA-Z0-9.-]+/[a-zA-Z0-9./_?&=%#-]*", str(obj["source_url"])):
            raise InputRejected("Source URL must be HTTPS")
        if obj["text_sha256"] != hashlib.sha256(text.encode("utf-8")).hexdigest():
            raise InputRejected("Tampered evidence text digest")
        indexed[eid] = obj
    checks = []
    for claim in claims:
        obj = _exact_keys(claim, {"id", "quoted_text", "evidence_ids"}, "claim")
        cid = _safe_string(obj["id"], "claim ID", 100)
        quote = _safe_string(obj["quoted_text"], "claim quote", 2000)
        ids = obj["evidence_ids"]
        if not isinstance(ids, list) or not ids or len(ids) > 20 or len(ids) != len(set(map(str, ids))):
            raise InputRejected("Claims must cite distinct evidence records")
        if not all(isinstance(x, str) and x in indexed for x in ids):
            checks.append({"claim_id": cid, "status": "MISSING_EVIDENCE", "evidence_ids": ids})
            continue
        matches = [indexed[x] for x in ids if quote in indexed[x]["text"]]
        status = ("UNSUPPORTED_QUOTE" if not matches else
                  "OPERATOR_REVIEW_REQUIRED" if not any(x["human_checked"] for x in matches)
                  else "EXACT_QUOTE_IN_OPERATOR_CHECKED_RECORD")
        checks.append({"claim_id": cid, "status": status, "evidence_ids": ids})
    if len({x["claim_id"] for x in checks}) != len(checks):
        raise InputRejected("Duplicate claim ID")
    return {"count": len(checks), "checks": checks,
            "unresolved": sum(x["status"] != "EXACT_QUOTE_IN_OPERATOR_CHECKED_RECORD" for x in checks),
            "operator_checked_is_source_authentication": False}


def evaluate(payload: object) -> dict:
    obj = _exact_keys(payload, {"schema", "synthetic", "model", "evaluation_rows", "evidence", "claims"}, "input")
    if obj["schema"] != SCHEMA or obj["synthetic"] is not True:
        raise InputRejected("Only synthetic model evaluation is supported")
    model = _exact_keys(obj["model"], {"id", "version", "task", "target_definition",
                                        "dataset_digest", "limitations"}, "model")
    for field in ("id", "version", "task", "target_definition"):
        _safe_string(model[field], field)
    if not re.fullmatch(r"[a-f0-9]{64}", str(model["dataset_digest"])):
        raise InputRejected("Model dataset digest must be SHA256 format")
    if not isinstance(model["limitations"], list) or not model["limitations"] or not all(
            isinstance(s, str) and 0 < len(s) <= 500 for s in model["limitations"]):
        raise InputRejected("Document model limitations")
    # Check that the declared dataset digest actually identifies these evaluation rows.
    # A valid-looking SHA string alone cannot establish a trustworthy model lineage.
    metrics = _evaluation(obj["evaluation_rows"])
    observed_digest = _digest(obj["evaluation_rows"])
    if model["dataset_digest"] != observed_digest:
        raise InputRejected("Model dataset digest does not match evaluation rows")
    grounding = _claims(obj["evidence"], obj["claims"])
    reasons = []
    if metrics["count"] < MIN_TEST_SET:
        reasons.append("INSUFFICIENT_INDEPENDENT_EVALUATION_ROWS")
    if metrics["brier"] > MAX_BRIER:
        reasons.append("BRIER_SCORE_EXCEEDS_THRESHOLD")
    if metrics["ece"] > MAX_ECE:
        reasons.append("CALIBRATION_ERROR_EXCEEDS_THRESHOLD")
    if metrics["segment_brier_spread"] is None:
        reasons.append("INSUFFICIENT_SEGMENT_COVERAGE")
    elif metrics["segment_brier_spread"] > MAX_GROUP_BRIER_GAP:
        reasons.append("SEGMENT_BRIER_GAP_EXCEEDS_THRESHOLD")
    if grounding["unresolved"] > 0:
        reasons.append("UNGROUNDED_OR_UNREVIEWED_CLAIMS")
    # These are supplied probabilities, with no model weights, feature attributions or
    # instance-level explanations. They cannot be called validated AI decisions.
    reasons.append("NO_INSTANCE_LEVEL_MODEL_EXPLANATIONS")
    return {"schema": OUTPUT_SCHEMA, "model": model, "dataset_digest_verified": True,
            "input_sha256": _digest(payload), "metrics": metrics,
            "evidence_audit": grounding, "policy": {
                "min_test_rows": MIN_TEST_SET, "max_brier": MAX_BRIER,
                "max_ece": MAX_ECE, "min_segment_rows": MIN_GROUP,
                "max_segment_brier_gap": MAX_GROUP_BRIER_GAP},
            "research_quality_gate": "MEETS_CONFIGURED_CHECKS" if not reasons else "REVIEW_REQUIRED",
            "explainability": {"per_prediction_rationale_available": False,
                               "feature_attributions_available": False,
                               "model_weights_or_inference_trace_verified": False,
                               "dataset_digest_authenticity_verified": False,
                               "claim_citations_checked_by_exact_text_only": True},
            "reasons": reasons, "external_release_authorized": False,
            "limitations": [
                "Synthetic demonstration; thresholds are illustrative and not actuarially approved.",
                "An exact quote match establishes textual traceability, not truth or legal authority.",
                "Operator marked evidence is not independently authenticated by this program.",
                "No model fitting, external data fetching, source verification or live inference occurs.",
                "Metrics are unweighted and do not establish market suitability or causal fairness."
            ]}


def write_result(input_path: Path, output_path: Path) -> dict:
    if output_path.suffix.lower() != ".json" or output_path.exists() or input_path.resolve() == output_path.resolve():
        raise InputRejected("Choose a new .json output path")
    if input_path.stat().st_size > 5000000:
        raise InputRejected("Input exceeds maximum file size")
    def no_duplicate_keys(pairs):
        obj = {}
        for key, value in pairs:
            if key in obj:
                raise InputRejected("Duplicate JSON field")
            obj[key] = value
        return obj
    raw = json.loads(input_path.read_text(encoding="utf-8-sig"), object_pairs_hook=no_duplicate_keys,
                     parse_constant=lambda x: (_ for _ in ()).throw(InputRejected("Nonfinite JSON value")))
    result = evaluate(raw)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("x", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False, allow_nan=False)
        f.write("\n")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--out-json", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = write_result(args.input, args.out_json)
    except (InputRejected, OSError, json.JSONDecodeError, TypeError, KeyError) as exc:
        print(f"Model assurance refused: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"output": str(args.out_json), "research_quality_gate": result["research_quality_gate"],
                      "reasons": result["reasons"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
