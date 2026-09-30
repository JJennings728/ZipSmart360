# Applied AI, Risk Analytics & Data Engineering Portfolio

**James Jennings | Insurance · Risk Management · Data Analysis · Applied AI**

Building practical systems at the intersection of **applied AI, insurance, risk analytics, data engineering, and decision support**.

This portfolio is organized around inspectable technical artifacts: architecture, assumptions, controls, tests, limitations, and implementation decisions are documented alongside the work.

## Featured work

### ZIPSmart360

**ZIP-level analytics pipeline and decision-support demonstration for structured geographic data.**

Python-based ingestion, validation, SQLite storage, SQL analytics, JSON API access, reproducible exports, automated testing, and an interactive dashboard.

**Python · SQL · SQLite · APIs · Testing · Data Engineering**

[Open ZIPSmart360](README.md) · [Read the evaluation memo](PORTFOLIO_EVALUATION.md)

### E&S Commercial Property — SQL + Power BI Underwriting

**Synthetic commercial-property underwriting decision-support project combining SQL, Power BI-ready modeling, DAX measures, exposure analysis, and transparent referral logic.**

Includes 30 synthetic submissions, a field-level data dictionary, SQL transformation layer, underwriting KPI definitions, requested-versus-quoted rate analysis, CAT and loss-quality screening, referral-queue logic, and dashboard design previews.

**E&S Property · SQL · Power BI · DAX · Underwriting Analytics · CAT Exposure**

[Open the SQL + Power BI underwriting project](powerbi-underwriting/README.md)

---
### Insurance AI Workflow Design

**Reference architecture and evaluation catalog for AI-assisted insurance operations.**

A structured library of insurance workflows translated into AI-agent tasks with defined inputs, expected outputs, prompt specifications, grading criteria, missing-information conditions, human-review requirements, and confidentiality controls.

**Applied AI · Agent Design · Prompt Engineering · Evaluations · Insurance Operations**

[Read the insurance portfolio case studies](INSURANCE_ANALYTICS_PORTFOLIO.md)

### Commercial CAT Exposure Data Engineering

**Synthetic commercial-property exposure cleansing and catastrophe-model readiness workflow.**

A clean-room reconstruction of a large-account exposure-data process demonstrating SOV normalization, TIV reconciliation, geocode-quality controls, construction/occupancy normalization, generalized peril segmentation, concentration analysis, and model-readiness review.

The public artifact uses 60 synthetic locations and contains no former employer, client, broker, vendor, address, contact, or confidential source record.

**Commercial Property · CAT Exposure · SOV · Data Quality · Risk Analytics · Excel**

[Read the CAT exposure case study](COMMERCIAL_CAT_EXPOSURE_PORTFOLIO.md)

### Facultative Reinsurance Pricing Model

**Transparent analytical model for facultative pricing and subscription analysis.**

Models expected-loss cost, technical premium, rate-on-line, market pricing, subscription share, and limit allocation with explicit assumptions and auditable formula logic.

**Reinsurance · Pricing Analytics · Financial Modeling · Risk Analysis**

[Read the insurance portfolio case studies](INSURANCE_ANALYTICS_PORTFOLIO.md)

### Aviation Underwriting Portfolio

**Synthetic aviation underwriting and subscription-market modeling case study.**

Demonstrates fleet exposure analysis, premium architecture, participation structure, underwriting assumptions, subjectivities, submission requirements, and analytical decision support using a fictional airline portfolio.

**Aviation Risk · Underwriting · Exposure Modeling · Insurance Analytics**

[Read the insurance portfolio case studies](INSURANCE_ANALYTICS_PORTFOLIO.md)

### Data Architecture Project

**Reference architecture for governed analytical data systems and AI-ready information pipelines.**

Explores ingestion, normalization, storage, data-quality controls, lineage, analytical interfaces, and the separation between source data, transformation logic, and downstream decision systems.

**Data Architecture · ETL · Governance · APIs · Analytics**

[Open the data architecture repository](https://github.com/JJennings728/data-architecture-project)

## Engineering pattern

The projects share a common pattern:

**Data → Validation → Analytics → Decision Logic → AI / Agents → Evaluation → Business Action**

The recurring design principles are:

- **Traceability:** inputs, assumptions, calculations, and outputs should be inspectable.
- **Validation:** invalid conditions should be identified before they propagate downstream.
- **Domain translation:** business and risk expertise should become explicit rules, schemas, workflows, and software behavior.
- **Human accountability:** analytical and AI systems should surface uncertainty and support professional judgment rather than hide it.

## Portfolio boundaries

Portfolio artifacts are demonstrations. Unless explicitly stated otherwise, they should not be interpreted as production carrier systems, deployed client solutions, actuarial opinions, insurance quotations, binding authority, or independently validated predictive models.

AI-assisted development is disclosed where applicable. The relevant standard is whether the artifact can be explained, tested, modified, reviewed, and defended at the code, data, and design level.

## Contact

[LinkedIn](https://www.linkedin.com/in/james-jennings-2053b4a8) · [GitHub profile](https://github.com/JJennings728)
