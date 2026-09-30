# E&S Commercial Property Underwriting — SQL + Power BI Portfolio

**James Jennings | E&S Insurance · P&C Risk · SQL · Power BI Analytics**

This synthetic commercial-property underwriting portfolio demonstrates how submission data can be converted into structured decision support using SQL, Power BI-ready modeling, DAX, exposure analytics, and transparent referral logic.

![Executive dashboard preview](docs/dashboard-overview.svg)

## Business decision

**Which submissions can proceed within demonstrated appetite, which require senior referral, and which should be declined or restructured based on exposure, catastrophe severity, protection, loss experience, capacity, and pricing context?**

The model organizes risk information for professional review; it does not replace underwriting judgment.

## What this demonstrates

- SQL transformation and portfolio aggregation
- Power BI-ready data modeling and DAX measures
- TIV and limit concentration analysis
- CAT severity, loss-ratio, protection, and hazard screening
- requested-versus-quoted rate analysis
- Quote / Refer / Decline workflow analytics
- explicit human-review reasons and auditable assumptions

## Repository structure

    powerbi-underwriting/
    ├── README.md
    ├── data/submissions.csv
    ├── data/DATA_DICTIONARY.md
    ├── sql/underwriting_model.sql
    ├── powerbi/measures.dax
    ├── powerbi/BUILD_GUIDE.md
    ├── powerbi-project/
    │   ├── ES-Commercial-Property-Underwriting.pbip
    │   ├── ES-Commercial-Property-Underwriting.Report/
    │   └── ES-Commercial-Property-Underwriting.SemanticModel/
    └── docs/*.svg

## Underwriting KPIs

| KPI | Purpose |
|---|---|
| Total TIV | Gross insured-value exposure |
| Total Limit | Requested deployed capacity |
| Quoted Premium | Rate-to-premium translation |
| Quote / Referral / Decline Rate | Workflow outcome mix |
| Weighted CAT Score | Exposure-weighted catastrophe severity |
| High CAT TIV % | Concentration in CATScore 8–10 |
| Average 3-Year Loss Ratio | Synthetic historical loss quality |
| Average Deductible | Insured risk retention |
| Rate Change % | Requested versus demonstrated quoted pricing |

## Power BI project

This repository now includes a **source-controlled Power BI Project (PBIP)** at:

`powerbi-project/ES-Commercial-Property-Underwriting.pbip`

The PBIP contains:

- a TMDL semantic model with the underwriting dataset schema and DAX measures;
- a local report-to-model `byPath` binding;
- three report pages;
- 16 PBIR visual definitions;
- Executive Underwriting, Referral & Appetite, and Pricing & Portfolio views; and
- a Power Query import that refreshes from the public synthetic CSV in this repository.

Open the `.pbip` file in a current Power BI Desktop build. Power BI Desktop can then save the same project as a proprietary `.pbix` if a binary deliverable is needed.

A `.pbix` binary is intentionally not fabricated outside Power BI Desktop.

## Dashboard previews

![Referral analysis preview](docs/referral-analysis.svg)

The SVGs are design previews generated from the same synthetic portfolio and are not falsely represented as Power BI Desktop captures. The PBIR/TMDL project source is separately included and inspectable. A true Power BI Desktop screenshot should only be added after the PBIP is opened and rendered in Power BI Desktop.

## Scope and limitations

All entities, brokers, submissions, rates, losses, hazard grades, CAT scores, values, and outcomes are synthetic. The decision and pricing logic is illustrative only. This is not an actuarial model, insurance quotation, binding authority, carrier guideline, or recommendation on an actual risk.

## Portfolio value

This artifact makes the claim **SQL & Power BI Analytics** independently reviewable: raw data, definitions, SQL transformations, DAX measures, KPI design, and the underlying business decision are visible and explainable.

## Source-control validation

The committed project has a valid PBIP-to-report pointer, a report-to-semantic-model relative binding, three registered pages, and 16 committed visual definitions. The project uses Microsoft's public PBIP/PBIR/TMDL file structure so the model and report logic can be reviewed in Git rather than hidden only inside a binary file.
