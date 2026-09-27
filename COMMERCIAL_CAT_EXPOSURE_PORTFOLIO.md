# Commercial CAT Exposure Data Engineering Case Study

**James Jennings | Commercial property · catastrophe exposure · data quality · risk analytics**

## Project summary

This project is a **clean-room synthetic reconstruction** of a historical large-commercial-account exposure-data workflow.

The original work involved a very large schedule of values and catastrophe-model preparation. Because historical workbooks can contain client locations, broker contacts, former-employer information, model-vendor terminology, and other non-public data, the public portfolio artifact does **not** publish or merely rename the source workbook.

Instead, the portfolio version reconstructs the transferable methodology with 60 synthetic locations.

## What the portfolio artifact demonstrates

### SOV normalization

The synthetic location table organizes core property-exposure fields into a consistent schema:

- account and location identifiers;
- city, state/region, and country;
- latitude and longitude;
- geocode quality;
- construction and occupancy;
- year built;
- stories and building count;
- building, contents, inventory, and business-interruption values; and
- generalized earthquake, wind, and flood hazard bands.

### TIV reconciliation

Each location calculates total insured value as:

**Building + Contents + Inventory + Business Interruption**

This makes the valuation components visible rather than treating TIV as an unexplained source field.

### Data-quality controls

The workbook deliberately includes several synthetic exceptions so the QA layer can identify:

- missing coordinates;
- missing year built;
- zero building value; and
- locations requiring review before downstream modeling.

Each location receives a **PASS** or **REVIEW** model-readiness status.

### Geospatial and peril segmentation

Synthetic locations are assigned generalized earthquake, wind, and flood hazard bands.

These categories are intentionally generic. They are **not** outputs from RMS, AIR, Moody's, Verisk, or another catastrophe-model vendor.

### Concentration analysis

The country summary aggregates:

- site count;
- total insured value; and
- percentage of portfolio TIV.

This demonstrates the transition from row-level exposure cleansing to portfolio-level concentration review.

### Model-request governance

A separate model-request brief records scope, requested perils, input standard, QA controls, output objective, and data classification.

That layer is important because a technically clean dataset can still be misused when modeling scope and assumptions are not explicit.

## Workbook architecture

The synthetic workbook contains six sheets:

| Sheet | Purpose |
| --- | --- |
| Portfolio Overview | Explains the project, skills demonstrated, and confidentiality guardrails |
| Assumptions | Defines the synthetic account, taxonomy, and calculation basis |
| Synthetic Locations | 60 synthetic property locations with formulas and QA status |
| Country Summary | Portfolio concentration by country |
| Quality Summary | Model-readiness and exception controls |
| Model Request | Synthetic CAT-model request brief and governance context |

## Skills demonstrated

- commercial property exposure analysis;
- catastrophe-model data preparation concepts;
- schedule-of-values cleansing;
- data normalization;
- TIV reconciliation;
- geocode and completeness QA;
- construction/occupancy normalization;
- peril-region segmentation;
- concentration analysis;
- spreadsheet engineering;
- model-readiness controls; and
- confidentiality-aware portfolio abstraction.

## Confidentiality design

The public artifact does **not** contain:

- the historical client name;
- the former employer name;
- broker or requestor identities;
- phone numbers or email addresses;
- real client street addresses;
- historical location identifiers;
- production TIV values;
- proprietary catastrophe-model output; or
- the original macro-enabled workbook.

The portfolio project was intentionally rebuilt rather than superficially anonymized.

## Portfolio boundary

This artifact demonstrates exposure-data engineering and risk-analysis concepts. It is not a catastrophe model, probable-maximum-loss study, actuarial analysis, insurance quotation, or production modeling submission.

[Return to the portfolio hub](PORTFOLIO.md)
