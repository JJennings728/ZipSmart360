from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI


REQUIRED_SECTIONS = (
    "account",
    "submission",
    "exposures",
    "loss_history",
    "delegated_authority",
    "facultative",
)

REQUIRED_REVIEW_KEYS = (
    "submission_readiness",
    "exposure_summary",
    "hull_asset_analysis",
    "missing_information",
    "risk_flags",
    "delegated_authority_review",
    "fac_review",
    "recommended_next_action",
    "human_review_required",
    "limitations",
)


def load_submission(path: str | Path) -> dict[str, Any]:
    """Load a UTF-8 JSON submission file."""
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("Submission must be a JSON object.")
    return data


def precheck_submission(data: dict[str, Any]) -> dict[str, Any]:
    """Run deterministic checks before any model call."""
    missing_sections = [name for name in REQUIRED_SECTIONS if name not in data]

    submission = data.get("submission")
    missing_documents: list[str] = []
    if isinstance(submission, dict):
        for key, value in submission.items():
            if key.endswith("_received") and value is False:
                missing_documents.append(key.removesuffix("_received").replace("_", " "))

    return {
        "schema_complete": not missing_sections,
        "missing_sections": missing_sections,
        "known_missing_documents": missing_documents,
    }


def build_prompt(data: dict[str, Any], precheck: dict[str, Any]) -> str:
    """Build a conservative underwriting-preparation prompt."""
    return f"""
You are reviewing a SYNTHETIC aviation / specialty-insurance submission for a
proof-of-value demonstration, with particular emphasis on commercial general
aviation, broker/MGA submission quality, delegated-authority referral controls,
hull concentration, and potential facultative-capacity review.

You are a decision-support component only. You do not have underwriting,
pricing, capacity, claims, legal, regulatory, or sanctions authority.

Rules:
1. Use only facts contained in the supplied JSON.
2. Clearly separate facts from assumptions or unknowns.
3. Do not invent missing limits, prices, loss details, CAT results, engineering
   findings, legal conclusions, or customer facts.
4. Do not recommend binding, quoting, declining, setting price, deploying
   capacity, or making a final coverage/claims decision.
5. Flag issues for an authorized human reviewer.
6. Treat hull values, pilot qualifications, utilization changes, delegated-
   authority thresholds, facultative-capacity questions, and other material
   exposures as review items rather than final conclusions.
7. When delegated-authority rules are supplied, compare the submission facts
   only to those supplied synthetic rules. Do not invent carrier appetite.
8. If a requested field is not applicable or cannot be supported by the
   submission, state that explicitly instead of inventing information.
9. Return VALID JSON ONLY. Do not wrap it in Markdown.

Return exactly these top-level keys:
- submission_readiness: object with "status" and "summary"
- exposure_summary: object with "aircraft_count", "total_hull_value_usd",
  "largest_single_aircraft_hull_usd", "requested_liability_limit_usd",
  "projected_flight_hours", "utilization_change_percent", and "summary"
- hull_asset_analysis: object with "status", "summary", and "issues"
- missing_information: array of strings
- risk_flags: array of objects with "category", "fact", "why_review"
- delegated_authority_review: object with "status", "summary", "reasons",
  and "disclaimer"
- fac_review: object with "summary" and "issues"
- recommended_next_action: string
- human_review_required: boolean (must be true)
- limitations: array of strings

Deterministic precheck:
{json.dumps(precheck, indent=2)}

Synthetic submission:
{json.dumps(data, indent=2)}
""".strip()


def parse_json_output(text: str) -> dict[str, Any]:
    """Parse model JSON, tolerating accidental fenced output."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    result = json.loads(cleaned)
    if not isinstance(result, dict):
        raise ValueError("Model output must be a JSON object.")

    missing = [key for key in REQUIRED_REVIEW_KEYS if key not in result]
    if missing:
        raise ValueError(f"Model output missing required keys: {missing}")

    if result.get("human_review_required") is not True:
        raise ValueError("Model output must require human review.")

    return result


def review_submission(
    data: dict[str, Any],
    client: OpenAI | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """Call the OpenAI Responses API and validate the returned review."""
    precheck = precheck_submission(data)
    client = client or OpenAI()
    model = model or os.getenv("OPENAI_MODEL", "gpt-6-luna")

    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "user",
                "content": build_prompt(data, precheck, reconciliation),
            }
        ],
    )

    if not response.output_text:
        raise RuntimeError("The model returned no text output.")

    return parse_json_output(response.output_text)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Synthetic aviation submission review proof of value."
    )
    parser.add_argument("submission", help="Path to submission JSON.")
    parser.add_argument(
        "--precheck-only",
        action="store_true",
        help="Run deterministic completeness checks without an API call.",
    )
    args = parser.parse_args()

    load_dotenv()
    data = load_submission(args.submission)
    precheck = precheck_submission(data)

    if args.precheck_only:
        print(json.dumps(precheck, indent=2))
        return

    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit(
            "OPENAI_API_KEY is not set. Use --precheck-only or configure the key locally."
        )

    result = review_submission(data)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
