from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory

from reconciliation import reconcile_case
from review_submission import precheck_submission, review_submission


BASE_DIR = Path(__file__).resolve().parents[1]
WEB_DIR = BASE_DIR / "web"
SAMPLE_DIR = BASE_DIR / "sample-data"

load_dotenv(BASE_DIR / ".env")

app = Flask(__name__, static_folder=str(WEB_DIR), static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024  # 2 MB demo limit
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)


@app.get("/")
def index():
    return send_from_directory(WEB_DIR, "index.html")


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.get("/sample-data/<path:filename>")
def sample_data(filename: str):
    return send_from_directory(SAMPLE_DIR, filename)


REFERENCE_REVIEW_FILES = {
    "SRP-DEMO-001": "example_review_output.json",
    "SRP-AIRLINE-DEMO-001": "example_airline_review_output.json",
}


def _load_reference_review(case_id: str) -> dict[str, Any]:
    filename = REFERENCE_REVIEW_FILES.get(case_id)
    if not filename:
        raise ValueError("No bundled reference review exists for this case.")
    with (SAMPLE_DIR / filename).open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("Reference review output must be a JSON object.")
    return value


@app.post("/api/analyze")
def analyze():
    payload: Any = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Upload a valid JSON object."}), 400

    if isinstance(payload.get("submission"), dict):
        submission = payload["submission"]
        evidence = payload.get("evidence")
        if evidence is not None and not isinstance(evidence, dict):
            return jsonify({"error": "Evidence package must be a JSON object."}), 400
    else:
        submission = payload
        evidence = None

    precheck = precheck_submission(submission)
    reconciliation = reconcile_case(submission, evidence) if evidence else None

    review_mode = "live_ai"
    if os.getenv("OPENAI_API_KEY"):
        try:
            review = review_submission(submission, reconciliation=reconciliation)
        except ValueError as exc:
            return jsonify({
                "error": str(exc),
                "precheck": precheck,
                "reconciliation": reconciliation,
            }), 422
        except Exception:
            logger.exception("Submission analysis failed")
            return jsonify({
                "error": "Analysis failed. Check the server log and configuration.",
                "precheck": precheck,
                "reconciliation": reconciliation,
            }), 500
    else:
        # Keep only the bundled synthetic proof-of-value demonstrable without credentials.
        # Uploaded non-synthetic submissions must not receive PrairieJet reference output.
        case_id = evidence.get("case_id") if isinstance(evidence, dict) else None
        expected_name_token = {
            "SRP-DEMO-001": "prairiejet",
            "SRP-AIRLINE-DEMO-001": "northstar",
        }.get(case_id)
        is_bundled_demo = (
            isinstance(evidence, dict)
            and case_id in REFERENCE_REVIEW_FILES
            and expected_name_token
            and expected_name_token in str((submission.get("account") or {}).get("name", "")).lower()
        )
        if not is_bundled_demo:
            return jsonify({
                "error": "OPENAI_API_KEY is not configured. The credential-free reference synthesis is available only for the bundled synthetic case.",
                "precheck": precheck,
                "reconciliation": reconciliation,
            }), 503

        try:
            review = _load_reference_review(case_id)
            review_mode = "reference_output"
        except Exception:
            logger.exception("Unable to load reference review output")
            return jsonify({
                "error": "OPENAI_API_KEY is not configured and reference output could not be loaded.",
                "precheck": precheck,
                "reconciliation": reconciliation,
            }), 503

    return jsonify({
        "precheck": precheck,
        "reconciliation": reconciliation,
        "review": review,
        "review_mode": review_mode,
    })


if __name__ == "__main__":
    app.run(
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8080")),
        debug=os.getenv("FLASK_DEBUG", "0") == "1",
    )
