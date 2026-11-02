# AeroCIE Phase 28 — Commercial demonstration report

Four populated, editable native PBIR pages replace the Phase 27 Overview scaffold. This is an internal synthetic demonstration, not a release authorization or an insurance decision system. Windows Power BI Desktop rendering and DAX execution remain **unverified**.

## Report contents

| Page | Contents and interaction |
| --- | --- |
| Executive Overview | Six model-driven KPI cards; advisory distribution; requested hull by aircraft; Low/Base/High comparisons and totals; evidence completeness; dynamic executive narrative. Submission and advisory slicers and chart selections filter case visuals. |
| Underwriting Risk Analysis | Aircraft, operation, label and evidence filters; submission decisions, requested hull, quality status and referral reasons; aircraft/pilot/utilization/MRO risk inputs; evidence distribution. Select a submission row to inspect inputs. |
| MRO & Severity Intelligence | Model, submission and category filters; weighted repair-delay indicators; scenario coverage; Low/Base/High comparisons; case-level cost pressure, parts availability and observation dates; explicit model limitations. |
| Evidence Quality & Source Integrity | Case evidence validation and issue codes; source registry with local snapshot hashes, as-of and retrieval timestamps; synthetic-source flags; limitations on digest validation and internal release. The registry and source KPIs deliberately remain dataset-wide. |

Every page has native page navigation, titles, keyboard tab order, alternative text and a visible synthetic/internal/human-review banner. The SRP theme uses navy, white, restrained cyan and Montserrat. Install Montserrat on the Windows workstation for the intended typography; Desktop may substitute a font when it is unavailable. All charts, cards and tables have editable semantic field bindings. There are no custom visuals, remote images, hardcoded displayed benchmark totals, generated HTML replacements or public services.

## Model and filter design

The original Power Query partitions, CSV folder parameter and existing DAX expressions are retained. Additional reporting measures provide selected-label counts using `KEEPFILTERS`, completeness, delay summaries, narrative and source-mode checks. Original advisory-count measures intentionally remain unchanged; report cards use `Selected Advisory Quote/Refer/Decline` so label selections intersect rather than replace context. Exposure totals come only from triage, never an addition of triage and severity hull columns. Currency formats are added to report-bound raw amount columns.

Three active one-to-one, bidirectional relationships join the existing triage snapshot to feature, severity and quality snapshots on `submission_id`. These are supported by complete, unique keys in fresh exports and a no-fanout regression. The graph is an acyclic hub; no manufacturer-only, model-only or source-registry relationships are inferred. Manufacturer/model MRO calculations retain their existing paired `TREATAS` logic. Source registry visuals are explicitly dataset-wide. Slicers are page-local; use each page's eraser controls to clear them before checking unfiltered benchmarks.

Evidence completeness means `insufficient_evidence=0`; it is not certification of source truth or underwriting suitability. Source Mode Check inspects imported flags only. It does **not** rerun CSV SHA-256 reconciliation, validate licensing or authorize release. The source registry stores synthetic snapshot hashes, not authenticated external-provider evidence. Missing scenario inputs remain blank, rather than fabricated zero-dollar outcomes.

## Linux validation

From `aviation-ai-workflow`, use the isolated Python environment and install the development validator when required:

```bash
python -m pip install -r requirements-dev.txt
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8 PYTHONDONTWRITEBYTECODE=1
python scripts/validate_powerbi.py
python -m pytest -p no:cacheprovider -q tests/test_aerocie_*.py tests/test_fr_*.py
run_dir=$(mktemp -d /tmp/aerocie-phase28.XXXXXXXX)
python -m src.aerocie.underwriting_pipeline --db "$run_dir/synthetic.db" --export-dir "$run_dir/powerbi-import"
python -m src.aerocie.underwriting_quality --db "$run_dir/synthetic.db" --out "$run_dir/quality-audit.json"
python -m src.aerocie.export_reconciliation --export-dir "$run_dir/powerbi-import"
```

The JSON validator uses bundled Microsoft schemas, their referenced dependency graph and SHA-256 checksums, with no network fallback. It validates PBIP, PBIR, PBISM, report metadata, pages, every visual container/query expression and the custom theme. A regression checks native visual role names and every bound table/column/measure, layout bounds/overlaps, interactions, relationships, DAX reference names and expression delimiters. These checks are not a DAX/TMDL runtime parser or an interactive rendering engine. Native visual formatting objects also require Desktop inspection because the generic PBIR schema permits extensible visual properties.

The original scaffold's nonexistent version-schema URL was corrected to Microsoft's `versionMetadata` schema and the report version set to the supported three-component format (`4.0.0`).

## Open and validate on Windows

1. Use a current Power BI Desktop installation supporting PBIP/PBIR and TMDL. Record the exact Desktop version in local acceptance evidence. Do not publish to Power BI Service.
2. In PowerShell, from `aviation-ai-workflow`, set UTF-8 and generate a fresh synthetic handoff in an exclusive temporary folder:

   ```powershell
   $env:PYTHONUTF8 = '1'
   $env:PYTHONIOENCODING = 'utf-8'
   $env:PYTHONDONTWRITEBYTECODE = '1'
   $run = Join-Path $env:TEMP ('AeroCIE-Phase28-' + [guid]::NewGuid().ToString('N'))
   New-Item -ItemType Directory -Path $run -ErrorAction Stop | Out-Null
   python -m src.aerocie.underwriting_pipeline --db "$run\synthetic.db" --export-dir "$run\powerbi-import"
   if ($LASTEXITCODE -ne 0) { throw 'Synthetic pipeline failed' }
   python -m src.aerocie.export_reconciliation --export-dir "$run\powerbi-import"
   if ($LASTEXITCODE -ne 0) { throw 'Reconciliation failed: stop before import' }
   ```

3. Open **`powerbi/AeroCIE-Underwriting.pbip`**. In Transform data → Manage parameters, set `AeroCIEDataFolder` to the generated `powerbi-import` folder **with a trailing backslash**. The checked-in Windows sample path is deliberately configurable and unchanged. Refresh all seven tables. Require a successful TMDL load and CSV import; do not save machine-specific paths into the shared branch.
4. In Model view, confirm the three one-to-one active relationships on `submission_id`, bidirectional filtering, and no additional auto-detected relationships. Confirm that source registry remains independent. Check each imported table's row counts and types.
5. With all page filters cleared, verify the following **synthetic acceptance benchmarks** against reconciliation, not against manually entered visual values:

   | Measure | Expected |
   | --- | ---: |
   | Synthetic submissions | 7 |
   | Advisory Quote / Refer / Decline | 2 / 4 / 1 |
   | Missing-evidence referrals | 2 |
   | Requested hull, not insured value | $34,045,000 |
   | Low / Base / High synthetic sensitivity | $46,243 / $104,080 / $208,159 |

6. On Overview, select Quote in the label slicer: submissions=2, Quote=2, Refer=0, Decline=0. Confirm hull/scenarios and narrative follow selection. Clear it, select a distribution bar, then clear again. Check exact currency totals and labels for clipping.
7. On Risk Analysis, choose aircraft and operation filters, select S006 and S007 separately, and inspect missing evidence, referral reasons and blank risk/scenario values. Check case IDs remain unique and hull totals do not multiply. Exercise evidence-status filtering and multi-selection.
8. On MRO, select an aircraft model, inspect paired-model weighted delay and compare selected Low/Base/High values with the exported CSV. Inspect blank MRO data and scenario coverage for missing-evidence submissions. Confirm that the charts are sensitivity comparisons, not claims forecasts.
9. On Evidence, filter cases by quality status. The case table and missing-evidence KPI must change, while the labelled dataset-wide source registry and source-mode KPIs remain unchanged. Inspect full SHA-256 strings using horizontal scrolling/column resizing. Check the offline gate again after any export changes.
10. Navigate all four pages. Inspect font fallback, layout, word wrapping, table scrolling, accessible titles, slicer erasers and chart interactions at normal and fit-to-page zoom. Use Ctrl+click for navigation buttons when required in edit mode. Capture screenshots and a pass/fail record for each page in local-only evidence.

## Remaining acceptance blockers

- Power BI Desktop import/TMDL parsing, DAX evaluation, visual rendering and formatting/cross-filter interaction must be verified on Windows. Linux static and Python results do not close this gate.
- The Windows workstation must supply its local CSV folder parameter and any desired Montserrat installation. No data-source credentials are needed for these synthetic local CSVs.
- CSV reconciliation must be rerun before each handoff; the report cannot certify original CSV digests from imported flags alone.

No claim calibration, commercial-data licensing, underwriting authority or external release is implied. Do not merge or distribute as Desktop-validated until Windows evidence is recorded.
