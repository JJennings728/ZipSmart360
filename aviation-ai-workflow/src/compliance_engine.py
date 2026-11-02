"""SRP Compliance Intelligence Engine: offline evidence triage; NOT legal advice.
Python 3.10+; standard library only; no API keys, network calls, or paid services.
Use exclusively with synthetic or authorized, non-sensitive business records.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def analyze(payload: dict) -> dict:
    """Flag missing provenance/evidence for human review; never determine compliance."""
    if not isinstance(payload, dict):
        raise ValueError("Input must be a JSON object")
    sources = payload.get("sources", [])
    evidence = payload.get("evidence", [])
    controls = payload.get("controls", [])
    if not all(isinstance(x, list) for x in (sources, evidence, controls)):
        raise ValueError("sources, evidence and controls must be arrays")
    for name, items in (("sources", sources), ("evidence", evidence), ("controls", controls)):
        if any(not isinstance(x, dict) or not isinstance(x.get("id"), str) or not x["id"].strip() for x in items):
            raise ValueError(f"Each {name} entry needs a nonempty string id")
        if len({x["id"] for x in items}) != len(items):
            raise ValueError(f"Duplicate {name} IDs")
    src = {s["id"]: s for s in sources}
    ev = {e["id"]: e for e in evidence}
    results = []
    for c in controls:
        flags = []
        ids = c.get("source_ids", [])
        ev_ids = c.get("evidence_ids", [])
        if not isinstance(ids, list) or not isinstance(ev_ids, list) or not all(isinstance(v, str) for v in ids + ev_ids):
            raise ValueError("source_ids and evidence_ids must be string arrays")
        if not ids:
            flags.append("NO_REGULATORY_SOURCE_MAPPED")
        for sid in ids:
            if sid not in src:
                flags.append(f"UNKNOWN_SOURCE:{sid}")
            else:
                s = src[sid]
                if not all(isinstance(s.get(k), str) and s[k].strip() for k in ("title", "url", "jurisdiction", "accessed_utc")):
                    flags.append(f"SOURCE_METADATA_INCOMPLETE:{sid}")
                if s.get("reviewer_verified") is not True:
                    flags.append(f"SOURCE_NOT_HUMAN_VERIFIED:{sid}")
        if not ev_ids:
            flags.append("NO_EVIDENCE_MAPPED")
        for eid in ev_ids:
            if eid not in ev:
                flags.append(f"UNKNOWN_EVIDENCE:{eid}")
            elif not isinstance(ev[eid].get("description"), str) or not ev[eid]["description"].strip():
                flags.append(f"EVIDENCE_DESCRIPTION_MISSING:{eid}")
        if c.get("applicability") not in ("human_confirmed_applicable", "human_confirmed_not_applicable"):
            flags.append("APPLICABILITY_NOT_HUMAN_CONFIRMED")
        results.append({
            "control_id": c["id"],
            "question": c.get("question", ""),
            "triage_status": "needs_documentation" if flags else "ready_for_human_review",
            "flags": sorted(set(flags)),
            "human_review_required": True,
        })
    counts = Counter(item["triage_status"] for item in results)
    return {
        "engine": "SRP-CIE offline evidence triage v0.1",
        "organization": payload.get("organization", "Unspecified (synthetic demo only)"),
        "regulatory_compliance_determination": "NOT_DETERMINED",
        "human_review_required": True,
        "summary": {"controls": len(results), "needs_documentation": counts["needs_documentation"],
                    "ready_for_human_review": counts["ready_for_human_review"]},
        "controls": results,
        "limitations": [
            "Source links and cited rules are supplied by the user; the engine does not retrieve or validate regulatory text.",
            "A reviewer_verified flag records an assertion, not independent verification by SRP.",
            "Missing evidence does not prove noncompliance; completed fields do not prove compliance.",
            "Authorized human review determines applicability, current law, adequacy of evidence, and next actions.",
            "No legal, safety, underwriting, pricing, or insurance placement decision is made.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline SRP compliance evidence triage; not compliance certification")
    parser.add_argument("input", help="Path to JSON input (synthetic or approved non-sensitive data only)")
    parser.add_argument("--output", help="Optional JSON report destination")
    args = parser.parse_args()
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    output = json.dumps(analyze(payload), indent=2)
    if args.output:
        Path(args.output).write_text(output + "\n", encoding="utf-8")
        print(f"Wrote {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
