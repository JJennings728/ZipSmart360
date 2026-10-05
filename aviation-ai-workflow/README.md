# StrategicRisk Partners — Aviation Underwriting Intelligence Proof of Value

A reference implementation for evaluating an **evidence-backed, AI-assisted aviation underwriting-intelligence workflow** using synthetic data.

> **Demonstration only.** This project contains synthetic information only. It is not a customer deployment, production underwriting system, legal/regulatory compliance determination, or authority to quote, bind, price, decline, settle, deploy capacity, or make another consequential insurance decision.

## Business problem

Aviation underwriting teams may receive information across submissions, aircraft schedules, insurance records, operator-authority material, aircraft records, loss histories, external event data, pilot information, and supporting correspondence.

Before an authorized underwriter makes a decision, teams may need to locate records, compare fields, resolve mismatches, identify missing evidence, and prepare a review-ready file. This workflow is a **hypothesis to validate with customer users**, not a claim about any specific insurer.

## What the prototype does

The prototype separates deterministic reconciliation from AI synthesis:

    Synthetic underwriting submission
                 +
    Authority / insurance / aircraft / event / filing evidence
                 |
                 v
    Deterministic validation + normalization
                 |
                 v
    Evidence reconciliation rules
                 |
                 +--> VERIFIED
                 +--> MISSING_EVIDENCE
                 +--> MISMATCH
                 +--> UNRESOLVED
                 +--> REFER
                 |
                 v
    Evidence-backed exception register
                 |
                 v
    Controlled AI-assisted synthesis
                 |
                 v
    Human disposition + audit trail

The model is not used to decide whether two identifiers match. Straightforward record comparison remains deterministic.

## Bundled synthetic cases

### PrairieJet Charter Group

The first bundled case represents **PrairieJet Charter Group (Synthetic)**, a fictional Part 135 / Part 91 operator with:

- 28 aircraft;
- USD 436 million stated fleet hull value;
- USD 500 million requested liability limit;
- 29.2% projected utilization increase; and
- incomplete supporting evidence.

The separate evidence package includes:

- synthetic Part 298 / operating-authority data;
- synthetic OST 6410-style insurance evidence;
- synthetic FAA-style aircraft registry records;
- synthetic aviation event history; and
- synthetic aircraft-change filing evidence.

Seven exception rules are intentionally planted so the prototype can be evaluated against known ground truth.

### Northstar Global Airlines

The second bundled case represents **Northstar Global Airlines (Synthetic)**, a fictional major Part 121 network airline with:

- 1,050 aircraft;
- USD 44.465 billion of synthetic stated fleet hull value;
- a USD 2.25 billion synthetic requested liability limit;
- global domestic, Atlantic, Pacific, and Latin America operations;
- large-airline operating metrics and fleet-transition complexity; and
- eight deliberately planted reconciliation exceptions.

Its scale is calibrated to public large-airline disclosures, including the United Airlines Holdings / United Airlines Q1 2026 Form 10-Q. It does **not** represent United Airlines' actual insurance program, losses, limits, fleet values, premium, deductibles, reinsurance, or underwriting information.

See `docs/major-airline-case-basis.md` for the public calibration methodology.

Synthetic performance is **not** a customer performance claim.

## Deterministic rule examples

The reference engine includes versionable rule IDs such as:

- `R-001` operator identity reconciliation;
- `R-002` FAA certificate-number reconciliation;
- `R-020` requested liability limit vs. supplied certificate evidence;
- `R-030` aircraft-scope reconciliation;
- `R-031` registration / serial reconciliation;
- `R-041` aircraft-change filing-evidence completeness;
- `R-054` external event vs. submitted loss-history reconciliation;
- `R-060` supporting-evidence completeness; and
- `R-070` synthetic delegated-authority referral conditions;
- `R-080` stated fleet count vs. aircraft schedule; and
- `R-081` fleet delivery-plan reconciliation.

These statuses are review signals, not legal compliance conclusions or actual carrier appetite.

## Browser workflow

The browser demonstration includes:

- one-click loading of the complete synthetic case;
- evidence-source inventory and source IDs;
- deterministic reconciliation checks;
- evidence-backed exception register;
- human disposition controls;
- session audit trail;
- synthetic ground-truth evaluation;
- AI-assisted underwriting synthesis;
- report preview;
- downloadable HTML report; and
- browser Print / Save as PDF.

When an `OPENAI_API_KEY` is configured, the synthesis layer calls the OpenAI Responses API. Without an API key, the **bundled synthetic case only** uses a clearly labeled repository reference output so the deterministic prototype remains demonstrable.

Uploaded non-synthetic submissions do not receive the PrairieJet reference output.

## Repository structure

    aviation-ai-workflow/
    ├── README.md
    ├── .env.example
    ├── requirements.txt
    ├── docs/
    │   ├── architecture.md
    │   ├── major-airline-case-basis.md
    │   ├── security-governance.md
    │   └── workflow.md
    ├── sample-data/
    │   ├── synthetic_submission.json
    │   ├── synthetic_evidence.json
    │   ├── example_review_output.json
    │   ├── synthetic_airline_submission.json
    │   ├── synthetic_airline_evidence.json
    │   └── example_airline_review_output.json
    ├── src/
    │   ├── reconciliation.py
    │   ├── review_submission.py
    │   └── server.py
    ├── web/
    │   ├── index.html
    │   ├── styles.css
    │   ├── report.js
    │   └── app.js
    └── tests/
        ├── test_reconciliation.py
        └── test_review_submission.py

## Quick start

Requires Python 3.11+.

    cd aviation-ai-workflow
    python -m venv .venv
    source .venv/bin/activate   # Windows: .venv\Scripts\activate
    pip install -r requirements.txt
    python src/server.py

Then open:

    http://127.0.0.1:8080

Choose either **Run major-airline case** or **Run Part 135 case**, then select **Run reconciliation**.

To use live AI synthesis, copy `.env.example` to `.env` and configure an API key locally. Never commit a real API key.

## Validation

The bundled case tests whether all seven intentionally planted exception rules are detected without unexpected exception rules.

A real design-partner proof of value should instead use a customer-approved answer key and agreed measures such as:

- extraction accuracy;
- reconciliation accuracy;
- exception recall;
- false-positive rate;
- unsupported-claim rate;
- reviewer correction rate;
- evidence traceability;
- review-cycle time; and
- reviewer usefulness.

No production performance claim should be made before representative customer-approved testing.

## Human-control boundary

The system does not independently:

- quote or bind insurance;
- set or approve price;
- deploy capacity;
- accept or decline risk;
- determine final coverage;
- decide claims;
- make sanctions determinations;
- make legal/regulatory compliance determinations; or
- replace actuarial, engineering, catastrophe-model, underwriting, or reinsurance judgment.

The bundled UI requires human disposition of exceptions and clearly labels the workflow as decision support.

## Design-partner pathway

See `docs/workflow.md` for a proposed **8–12 week design-partner proof of value**, including discovery, answer-key creation, controlled implementation, evaluation, and optional scale assessment.

See `docs/architecture.md` for the evidence-reconciliation architecture and `docs/security-governance.md` for production-readiness considerations.

## Status

**Working reference implementation / synthetic-data proof of value.**

It should be described as a prototype or proof of value—not as a customer implementation—unless and until it is actually delivered and validated with a customer.
