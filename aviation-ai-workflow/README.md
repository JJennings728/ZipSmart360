# StrategicRisk Partners — Aviation Underwriting Intelligence Proof of Value

A reference implementation for evaluating an **AI-assisted commercial aviation underwriting-intelligence workflow** using synthetic data and the OpenAI Responses API. The demonstration is designed around broker, MGA, delegated-authority, specialist-carrier, and facultative-review workflows.

> **Demonstration only.** This project uses synthetic information. It does not contain customer, carrier, broker, prior-employer, or personally identifiable information. It is not represented as a customer deployment, production underwriting system, or authority to quote, bind, deny, settle, or otherwise make consequential insurance decisions.

## Business problem

Commercial aviation teams may receive submissions spread across applications, aircraft schedules, pilot schedules, loss runs, operating specifications, safety and maintenance documentation, policy wording, and facultative or excess-capacity materials. Before a senior underwriter can make a decision, analysts and underwriters may need to:

- identify missing submission items;
- normalize key exposure information;
- distinguish attritional losses from large or catastrophe losses;
- flag wording or facultative-reinsurance issues;
- identify concentration, BI/CBI, CAT, and special-hazard concerns; and
- prepare a review-ready summary.

This proof of value demonstrates a controlled workflow that assists with **completeness checking, extraction, synthesis, and exception flagging** while preserving human underwriting authority.

## What the demo does

    Synthetic submission JSON
            |
            v
    Local completeness / schema pre-check
            |
            v
    OpenAI Responses API
            |
            v
    Structured review output
            |
            v
    Mandatory human underwriting review

The model is instructed to produce a review package containing submission readiness, a commercial-aviation exposure summary, hull and asset observations, missing-information requests, risk flags, illustrative delegated-authority referral analysis, FAC / capacity review, a recommended next action, and explicit limitations.

## Synthetic commercial GA scenario

The included sample represents **PrairieJet Charter Group (Synthetic)**, a fictional Part 135 / Part 91 operator with 28 aircraft, USD 436 million of stated hull value, a USD 500 million requested liability limit, a 29.2% projected utilization increase, incomplete supporting information, and intentionally exceeded **synthetic** delegated-authority thresholds. The scenario is designed to demonstrate referral logic and underwriting preparation—not actual carrier appetite or authority.

## What the demo does not do

It does **not** quote or bind insurance, set rates or authorize capacity, make final coverage determinations, replace CAT/actuarial/engineering/sanctions/legal/regulatory review, make autonomous consequential decisions, or process real customer data by default.

## Repository structure

    aviation-ai-workflow/
    ├── README.md
    ├── .env.example
    ├── requirements.txt
    ├── docs/
    │   ├── architecture.md
    │   ├── security-governance.md
    │   └── workflow.md
    ├── sample-data/
    │   ├── synthetic_submission.json
    │   └── example_review_output.json
    ├── src/
    │   ├── review_submission.py
    │   └── server.py
    ├── web/
    │   ├── index.html
    │   ├── styles.css
    │   ├── report.js
    │   └── app.js
    └── tests/
        └── test_review_submission.py

## Quick start

Requires Python 3.11+.

    cd aviation-ai-workflow
    python -m venv .venv
    source .venv/bin/activate   # Windows: .venv\Scripts\activate
    pip install -r requirements.txt

Copy `.env.example` to `.env` and add your API key locally. Never commit a real API key.

Run the local completeness check without an API call:

    python src/review_submission.py sample-data/synthetic_submission.json --precheck-only

Run the AI-assisted review:

    python src/review_submission.py sample-data/synthetic_submission.json

The code uses the OpenAI **Responses API**. The default model can be changed with `OPENAI_MODEL`.


## Browser demo

The repository now includes a lightweight browser interface for live demonstrations. The API key remains on the server; it is never requested or stored by the browser.

After installing requirements and configuring `.env`, start the local demo server:

    python src/server.py

Then open:

    http://127.0.0.1:8080

The browser workflow provides:

- JSON upload and drag-and-drop;
- a one-click **28-aircraft synthetic Part 135 charter sample**;
- Analyze submission;
- Submission Readiness;
- Commercial GA Exposure Summary;
- Hull & Asset Analysis;
- Missing Information;
- Risk Flags;
- Delegated Authority & Referral Review;
- FAC / Capacity Review;
- Recommended Next Action;
- a prominent Human Review Required control;
- a polished in-app preview of the generated review report;
- a self-contained downloadable HTML review report; and
- a print-optimized report view for browser **Print / Save as PDF**.

The UI posts either a submission-only JSON object or a `{ submission, evidence }` package to `/api/analyze`. When evidence is supplied, the Flask server runs deterministic reconciliation first and passes that evidence context into the controlled AI review. The included synthetic case can still demonstrate the deterministic workflow with repository reference synthesis when no API key is configured; uploaded non-synthetic cases require a configured API key for AI synthesis.

After a successful analysis, **Preview review report** opens a full in-app report preview generated from the current analysis. From that preview, **Download HTML** creates a self-contained branded report and **Print / Save PDF** opens the same report in a print-optimized window so it can be saved as a PDF without sending the report to an additional server-side PDF service. The report includes exposure metrics, hull analysis, missing information, risk flags, delegated-authority referral logic, FAC review, Human Review Required, and Recommended Next Action.

**Security note:** the demo is intended for local proof-of-value use with synthetic or explicitly customer-approved data. Do not expose the development server publicly or place API credentials in browser code.

## Validation approach

A proof of value should be evaluated against agreed criteria rather than subjective impressions. Recommended measures include completeness recall, extraction accuracy, unsupported-claim rate, reviewer usefulness, human-review compliance, and controlled cycle-time comparison.

No performance claim should be made until measured with representative customer-approved examples.

## Governance principles

1. **Human-in-the-loop:** final underwriting, pricing, capacity, claims, coverage, sanctions, legal, and regulatory decisions remain with authorized people.
2. **Data minimization:** provide only information required for the use case.
3. **Access control:** production access should follow least privilege and customer-approved identity controls.
4. **Auditability:** retain appropriate records of source material, model output, reviewer action, and final disposition.
5. **Validation:** test extraction errors, unsupported statements, omissions, and failure modes before production.
6. **Change control:** model, prompt, schema, and integration changes should be versioned and revalidated.

See `docs/security-governance.md` for the production-readiness checklist.

## Intended commercial use

StrategicRisk Partners can use this repository as a **technical demonstration and discovery asset** when discussing commercial aviation submission intelligence, delegated-authority controls, underwriting workflow modernization, and facultative/capacity review.

A real customer engagement should begin with the customer's workflow, business problem, evidence of pain, success measures, security/governance requirements, and agreed next validation step. Production implementation should be separately scoped and approved.

## Status

**Reference implementation / synthetic-data demonstration.**

The project demonstrates workflow architecture, API integration, local validation, testing, governance, and human-review controls. It should not be described as a customer implementation unless and until it has actually been delivered for a customer.