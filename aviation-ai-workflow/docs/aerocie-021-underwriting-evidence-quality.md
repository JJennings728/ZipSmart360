# AeroCIE-021 | Underwriting evidence integrity and submission quality

**Scope:** One integrated aviation underwriting product. This milestone adds a read-only evidence quality audit to the existing local, synthetic GA triage, MRO sensitivity, Power BI export, and report preview modules.

## Implemented

1. The ingestion pipeline writes a local SHA-256 record for each of four fact-source datasets (MRO, submissions, NTSB model aggregates, SWIM operations), the source registry, three dimension tables, and the scoring policy. Each dataset is checked against its registered value during report and CSV generation. A local hash detects subsequent changes; it does **not** certify that a provider supplied authentic or licensed data.
2. The quality audit identifies invalid submission dates, airframes built after their submission date, contradictory pilot hours, missing pilot and training evidence, missing hull value, missing MRO data, and stale or future MRO observations.
3. A changed source, dimension, or policy blocks the report and Power BI export. The standalone audit command still writes a diagnostic JSON for investigation.
4. Missing evidence produces an advisory `Refer` and a missing score. The dashboard lists the individual reasons alongside a nine-dataset fingerprint indicator. `INPUTS_PRESENT_SYNTHETIC` means that required fields were present under the sample policy, not that risk was adequately priced.
5. Power BI exports include `submission_quality.csv`, `quality_audit.json`, and a manifest with the quality gate. The PBIP semantic model defines the new `submission_quality` import table.
6. No model calibration, claim forecast, actual underwriting approval, or data acquisition contract is implied.

## Test on Windows

From the root of `aviation-ai-workflow` on the Phase 25 draft branch:

```powershell
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\validate-phase25.ps1 -Python "C:\PATH\TO\.venv\Scripts\python.exe" -OpenDemo
```

The runner writes to a fresh directory beneath `DocumentsSRP-AeroCIE`, tests AeroCIE plus Federal Register modules, generates a new sample SQLite database, verifies all source hashes, exports Power BI CSV files and opens the HTML dashboard.

In Power BI Desktop, update `AeroCIEDataFolder` to the generated `powerbi-import` directory (with trailing backslash), then refresh the semantic model. Import `submission_quality` into the dashboard so underwriters can filter by `Refer` reason. The report page definition is still a scaffold and needs visual wiring in Power BI Desktop.

## Quality acceptance criteria

- All fact-source, dimension, registry, and policy checks show `FINGERPRINT_MATCH_ONLY`.
- The original seven synthetic cases show five cases with required inputs and two with explicit referral reasons.
- Tampering a facility wait time, an aircraft value, a source digest, or the scoring policy blocks the customer-style preview and CSV export.
- Contradictory pilot hours, impossible aircraft year, and invalid submission dates are identified and stop the preview.
- Missing hull value causes a `Refer` label and a blank sensitivity scenario.
- An MRO observation more than 30 days old produces a referral.
- No claims of predictive loss reduction, real-world accuracy or quote/bind authority.

## Next work required to complete the product

1. Connect licensed aviation sources and record their retrieval receipts and permitted use terms. FAA SWIM does not supply private pilot records or MRO inventory data; those require separate authorized inputs.
2. Add approved customer intake and persistent case handling, with user access and versioned revision history.
3. Validate input coverage against real cases and loss outcomes using retrospective evaluation and out-of-time testing. Set acceptable false negative and referral thresholds with underwriting customers.
4. Finish Power BI Desktop report wiring, calculate and reconcile DAX versus SQLite on the same cases, and document refresh behavior.
5. Conduct controlled pilot testing with documented response and operational metrics.
