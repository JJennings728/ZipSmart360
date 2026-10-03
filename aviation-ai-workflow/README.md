# StrategicRisk Partners — Aviation & Specialty Insurance AI Workflow Proof of Value

A reference implementation for evaluating an **AI-assisted aviation / specialty-insurance submission review workflow** using synthetic data and the OpenAI Responses API.

> **Demonstration only.** This project uses synthetic information. It does not contain customer, carrier, broker, prior-employer, or personally identifiable information. It is not represented as a customer deployment, production underwriting system, or authority to quote, bind, deny, settle, or otherwise make consequential insurance decisions.

## Business problem

Aviation and specialty-insurance teams may receive submissions spread across slips, schedules, loss runs, engineering reports, policy wording, CAT outputs, and facultative reinsurance documents. Before a senior underwriter can make a decision, analysts and underwriters may need to:

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

The model is instructed to produce a review package containing submission readiness, missing-information requests, exposure and loss-history observations, FAC / wording issues, risk flags, a recommended next action, and explicit limitations.

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
    │   └── review_submission.py
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

StrategicRisk Partners can use this repository as a **technical demonstration and discovery asset** when discussing an Aviation & Specialty Insurance AI Workflow Assessment + Proof of Value.

A real customer engagement should begin with the customer's workflow, business problem, evidence of pain, success measures, security/governance requirements, and agreed next validation step. Production implementation should be separately scoped and approved.

## Status

**Reference implementation / synthetic-data demonstration.**

The project demonstrates workflow architecture, API integration, local validation, testing, governance, and human-review controls. It should not be described as a customer implementation unless and until it has actually been delivered for a customer.