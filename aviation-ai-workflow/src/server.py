from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory

from review_submission import precheck_submission, review_submission


BASE_DIR = Path(__file__).resolve().parents[1]
WEB_DIR = BASE_DIR / "web"

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


@app.post("/api/analyze")
def analyze():
    payload: Any = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Upload a valid JSON object."}), 400

    precheck = precheck_submission(payload)

    if not os.getenv("OPENAI_API_KEY"):
        return jsonify({
            "error": "OPENAI_API_KEY is not configured on the server.",
            "precheck": precheck,
        }), 503

    try:
        review = review_submission(payload)
    except ValueError as exc:
        return jsonify({"error": str(exc), "precheck": precheck}), 422
    except Exception:
        logger.exception("Submission analysis failed")
        return jsonify({
            "error": "Analysis failed. Check the server log and configuration.",
            "precheck": precheck,
        }), 500

    return jsonify({"precheck": precheck, "review": review})


if __name__ == "__main__":
    app.run(
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8080")),
        debug=os.getenv("FLASK_DEBUG", "0") == "1",
    )
