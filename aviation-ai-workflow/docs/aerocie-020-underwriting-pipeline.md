# AeroCIE-020 | Aviation underwriting decision support

**Scope:** one modular AeroCIE product combining synthetic general aviation submission triage, MRO repair delay indicators, source tracking, and Power BI import tables. The module is under development and uses no live feeds.

## Delivered implementation

- `sql/underwriting_schema.sql` defines `dim_aircraft`, `dim_pilot`, `dim_mro_facility`, `fact_mro_constraints`, `fact_underwriting_submissions`, `fact_ntsb_model_context`, `fact_swim_operations`, `source_registry`, and `model_policy`.
- `src/aerocie/underwriting_pipeline.py` generates a reproducible synthetic fixture, creates a SQLite DB at a new path and exports eight allowlisted CSV views and a SHA-256 manifest.
- `src/aerocie/underwriting_preview.py` generates a static HTML dashboard, with traceable factors and review labels.
- `powerbi/AeroCIE-Underwriting.pbip` contains a starter Power BI project, semantic model and an overview report; see `powerbi/dax/AeroCIE_Exact_DAX_Measures.md` for the measures. Power BI Desktop validation remains necessary before promising a supported PBIP experience.
- `src/aerocie/pilot_evaluation.py` compares an illustrative AeroCIE triage label with a baseline on 50 synthetic retrospective cases, including adverse-outcome detection, false negatives, unknown outcomes and measured analyst minutes.
- `src/aerocie/pilot_economics.py` computes labor savings scenarios, subscription cost and break-even quote volume from supplied assumptions.

## Data meaning

| Input | Used for | Exclusions and qualification |
| --- | --- | --- |
| Submission aircraft and use | Aircraft age, class and operating profile | No underwriting appetite or coverage authority |
| Pilot certification, hours, training | Test heuristic points and identify missing evidence | Synthetic fields; no FAA pilot history download, personal records, or verification |
| MRO facility observation | Wait-time and parts availability weighted proxy | Simulated facility data; not observed global repair capacity or predicted claim value |
| NTSB-like model aggregate | Context in separate import table | Model-wide illustrative aggregate, not a pilot-specific claims rate |
| SWIM-like operations | Context in separate import table | Synthetic counts; SWIM does not directly provide pilot or MRO maintenance histories |

The view `v_submission_triage` returns advisory labels `Quote`, `Refer`, or `Decline`. A decline label calls for underwriting review; it is not an automatic refusal of coverage. The policy has `approved_for_automatic_binding=0`. Missing or out-of-date evidence returns `Refer` with a null numeric score. Heuristic thresholds have not been trained or calibrated against loss data and may exhibit selection bias.

## Run a demonstration

From `aviation-ai-workflow`:

```powershell
$Python = "C:\FULL\PATH\TO\.venv\Scripts\python.exe"
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\validate-phase24.ps1 -Python $Python -OpenDemo
```

The runner writes a fresh SQLite file, HTML report, CSV extracts, synthetic outcome evaluation and economic scenario under Documents. Original source databases remain at their prior paths. Running the same command again creates another unique directory.

## Data pipeline extensions before customer use

1. Agree specific feed licenses and their permitted use. FAA SWIM is a collection of operational data streams rather than a pilot qualification or global MRO availability dataset. NTSB investigations need accident, exposure and coverage normalization before risk comparisons.
2. Obtain approved primary or client-supplied source files with acquisition timestamps, immutable checksums, provenance, permitted use and dataset versions.
3. Measure missing fields, stale data, model calibration, false negatives, subgroup performance, and analyst overrides against a blinded historical baseline.
4. Integrate the export into an insurer's configured Power BI environment, test DAX and PBIP import, and reconcile each visible measure to SQLite for the same case.
5. Define underwriter appetite and referral thresholds only with a customer's authorized underwriting team.

## Sales linkage

Read `docs/aerocie-020-paid-pilot-offer.md` for a 60-day paid pilot proposal and `docs/aerocie-020-pricing.md` for subscription hypotheses. Until a real historical evaluation is authorized and measured, example minutes, scorecards, benefit claims and data are synthetic and exploratory.
