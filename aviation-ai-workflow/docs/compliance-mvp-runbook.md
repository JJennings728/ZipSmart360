# CIE v0.1 — Offline prototype runbook

## Purpose and technical boundary
Runs completely offline in Python 3.10+ without credentials, paid cloud, OpenAI API, or extra Python packages. Complements rather than replaces the existing synthetic underwriting proof of value.

## Windows PowerShell
From repository root:

    cd aviation-ai-workflow
    python -m unittest discover -s tests -p test_compliance_engine.py -v
    python src/compliance_engine.py sample-data/synthetic_compliance_input.json --output sample-report.json
    notepad sample-report.json

The example contains synthetic evidence and regulator URL references for discovery only. It is not a regulatory interpretation. No private customer data should be used in the public repo or development chat.

## Input schema
JSON object with organization, arrays named sources, evidence, controls. Each entry requires unique id. Source metadata includes title, url, jurisdiction, accessed_utc and reviewer_verified (an *assertion*, not independent verification). Controls reference source_ids and evidence_ids; applicability is unassessed unless an authorized human recorded human_confirmed_applicable or human_confirmed_not_applicable.

## Output
For each control, the engine identifies unknown sources, missing metadata, unverified sources, missing evidence and applicability not yet human-confirmed. Every output requires human review. regulatory_compliance_determination is always NOT_DETERMINED. ready_for_human_review is NOT a compliance pass.

## No-go controls
- No live regulator scraper or continuous update promise.
- No legal, safety, maintenance, coverage, sanctions, claims, underwriting or pricing determinations.
- No customer personal information, proprietary records or credentials without a separately approved secure setup.
- Do not conflate statute/regulation, adopted state bulletin, FAA guidance, NAIC model, trade association guidance or proposed policy.
- Human confirmation must use current primary documents and state/operational applicability.
- No paid API required for initial validation.

## Next milestone
One source-cited example report with a verified version/date ledger, mapped review questions, source text vs inference distinction and documented human dispositions. Gather buyer feedback before investing in a hosted platform.
