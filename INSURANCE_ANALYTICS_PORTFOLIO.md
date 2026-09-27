# Insurance Analytics & Underwriting Portfolio

**James Jennings | Insurance, risk management, data analysis, and AI workflow design**

This page documents three workbook-based portfolio case studies that complement the executable [ZIPSmart360](https://github.com/JJennings728/ZipSmart360) project. These artifacts demonstrate insurance-domain modeling, spreadsheet engineering, prompt/workflow design, underwriting reasoning, and technical communication.

They are **portfolio demonstrations**, not production carrier systems, actuarial opinions, live client work, binders, quotations, or representations of available insurance terms.

---

## 1. Facultative Reinsurance Pricing Model

### Purpose

A repaired and restructured facultative pricing workbook that shows how a small set of explicit assumptions can be translated into transparent pricing outputs.

### Model inputs

The portfolio version separates hardcoded assumptions from calculated outputs:

- facultative layer limit;
- 100% market premium;
- total insured value;
- expected-loss rate;
- layer exposure factor;
- expense/profit/risk-margin loadings; and
- reinsurer subscription share.

The original workbook contained broken cell references that produced `#VALUE!` errors. The repaired version replaces those references with explicit formula logic and normalizes the subscription assumption to **1%**.

### Calculations demonstrated

The model calculates:

- modeled expected-loss cost;
- technical premium after loadings;
- technical rate on line;
- market rate on line;
- market-versus-technical multiple;
- premium adequacy margin;
- market premium at the subscribed share; and
- layer limit at the subscribed share.

Using the current illustrative assumptions, the model produces approximately:

| Metric | Illustrative result |
| --- | ---: |
| Modeled expected-loss cost | $61,148 |
| Technical premium | $97,060 |
| Technical rate on line | 0.121% |
| Market rate on line | 5.454% |
| Market premium at 1% share | $43,630 |
| Limit at 1% share | $800,000 |

The large gap between the modeled technical premium and the market premium is itself an important modeling lesson: a mathematically correct spreadsheet can still be commercially meaningless if the expected-loss and exposure assumptions are not actuarially supported.

### Skills demonstrated

- spreadsheet-model repair;
- facultative/reinsurance terminology;
- assumption separation;
- rate-on-line analysis;
- subscription-share calculations;
- error control and model transparency; and
- distinguishing a portfolio calculation from actuarial pricing.

---

## 2. Insurance AI Workflow Design & World-Building Catalog

### Purpose

A structured design library for insurance-focused AI workflows. The workbook turns insurance functions into repeatable tasks with defined inputs, expected outputs, prompt specifications, and evaluation criteria.

### Scope

The catalog contains:

- **42 workflow concepts**;
- **12 prioritized starter workflows**; and
- **4 detailed prompt-and-grading examples**.

The workflow set spans underwriting, claims, actuarial/reserving, reinsurance, compliance, renewal strategy, commercial property, commercial auto, cyber, D&O, E&O, submission triage, subrogation, and related insurance functions.

### World-building approach

The portfolio uses a fictional insurance environment centered on **Northstar**, allowing multiple workflows to share a consistent insured, operating context, and risk profile without exposing real client information.

This demonstrates a form of technical world-building: constructing enough persistent business context that an AI system can be evaluated on realistic multi-step insurance work rather than disconnected prompts.

### Workflow-design method

Each workflow can specify:

- required data sources;
- expected deliverables;
- user prompt;
- grading/evaluation guidance;
- difficulty levers;
- missing-information conditions;
- human review requirements; and
- confidentiality boundaries.

The recommended set emphasizes tasks where quality depends on judgment rather than simple extraction, including renewal underwriting, SOV validation, property risk assessment, rate indication, D&O, cyber, subrogation, policy compliance, and reserve analysis.

### Skills demonstrated

- AI task and agent workflow design;
- prompt engineering;
- evaluation-rubric design;
- insurance process taxonomy;
- multi-step task decomposition;
- synthetic-world construction;
- data-source mapping;
- human-in-the-loop controls; and
- confidentiality-aware portfolio design.

---

## 3. Aviation Hull & Liability Underwriting Case Study

### Purpose

A fictionalized airline insurance case study that models the workflow from fleet exposure through indicative premium construction, underwriting subjectivities, submission gaps, and application-field requirements.

The public portfolio identity is **Northstar Air Group**. Pricing, fleet values, rates, and capacity assumptions are training assumptions only.

### Workbook architecture

The case study includes:

**Quote Summary** — an executive view of the mock placement, premium components, subscription-share scenarios, terms, and underwriting notes.

**Fleet Valuation** — aircraft-level modeling of in-service and storage exposure, assumed hull value, hull TIV, liability unit charges, war/allied-perils amounts, and total indicated premium.

**Premium Model** — rolls hull, storage, spare-parts, liability, and war components into a 100% annual indication and participating insurer share.

**Terms & Conditions** — tracks underwriting subjectivities involving valuation, five-year losses, safety management, MRO/maintenance, territory, passenger liability, cyber resilience, war exposure, and subscription-market several liability.

**Submission Gaps** — prioritizes missing data and explains why each missing item matters to pricing, coverage, or binding authority.

**Application Map** — connects aviation-application fields to underwriting use and quality-assurance checks.

**Sources** — distinguishes fictionalized data, generic application concepts, public-style market themes, and editable model assumptions.

### Skills demonstrated

- specialty aviation underwriting concepts;
- fleet and hull exposure modeling;
- premium-component architecture;
- subscription-market structure;
- underwriting subjectivity management;
- missing-data / submission-gap analysis;
- application design and QA;
- spreadsheet-based executive reporting; and
- communicating model limitations.

---

## How these projects fit together

These workbook projects and ZIPSmart360 show two sides of the same skill set.

**ZIPSmart360** demonstrates executable engineering: Python, SQL, data validation, APIs, automated tests, and reproducibility.

The **insurance portfolio artifacts** demonstrate domain translation: identifying how insurance judgment, controls, submissions, pricing assumptions, and workflow requirements should be represented in structured technical systems.

The common theme is controlled decision support:

1. define the inputs;
2. validate what can be validated;
3. make assumptions explicit;
4. calculate or reason transparently;
5. surface missing information;
6. distinguish facts from assumptions;
7. test failure conditions; and
8. communicate limitations before a result is used.

That combination is particularly relevant to insurance technology, risk engineering, data/AI product work, and technical roles involving regulated or high-consequence business processes.

## Portfolio boundaries

These artifacts should not be represented as production carrier systems, independently developed actuarial models, real client deliverables, or deployed underwriting authority.

They are portfolio demonstrations intended to show how insurance-domain knowledge can be translated into structured models, technical workflows, and reviewable artifacts.

---

**Primary executable project:** [ZIPSmart360](https://github.com/JJennings728/ZipSmart360)

**Project evaluation:** [ZIPSmart360 Portfolio Evaluation](PORTFOLIO_EVALUATION.md)
