# AeroCIE-027 | Power BI Desktop reporting and acceptance

**Status: Draft. Windows Python regression tests and CSV reconciliation passed for Phase 26. Power BI Desktop rendering and DAX execution have NOT been verified.**

Phase 28 adds the populated four-page report. See [Phase 28 implementation and Windows validation](aerocie-028-commercial-dashboard.md). The scaffold status below records Phase 27 history; it is not the current report content.

## Scope

This feature adds 11 explicit DAX measures to the existing PBIP semantic model. The underlying report page remains a scaffold. The files do not create a signed, distributable PBIX or a hosted dashboard.

### Readiness gates

1. Use the Phase 25 validator on the current branch to produce a fresh **synthetic-only** export directory. Never substitute actual pilot, customer, loss, or licensed provider data.
2. Run `python -m src.aerocie.export_reconciliation --export-dir "<export-folder>"`. STOP unless status=PASS, release_authorized=false, 10 manifest CSV digests match (including submission quality on the Phase 28 branch), and seven case IDs reconcile.
3. Open the existing `powerbi/AeroCIE-Underwriting.pbip` project in Power BI Desktop, if that exact entrypoint exists locally. Otherwise open the .Report project using Desktop's supported PBIP workflow. Set semantic parameter `AeroCIEDataFolder` to your generated `powerbi-import` folder with a trailing backslash.
4. Refresh every semantic-model table. Inspect any TMDL validation errors in Desktop; Python static tests do not validate DAX or the actual TMDL runtime.
5. Add KPI cards for Synthetic Submissions, Advisory Quote, Advisory Refer, Advisory Decline, Missing Evidence, and Requested Hull Total Not Insured.
6. Add a scenario sensitivity group containing Scenario Low Synthetic, Scenario Base Synthetic, Scenario High Synthetic. Label it *Assumption-based synthetic repair-cost sensitivity, not a claim forecast*.
7. Add a submission table with submission_id, aircraft/model, triage_recommendation, risk_points, submission_quality.issue_codes, and the three scenario amounts. **Before combining tables** define and verify one-to-one submission_id relationships where applicable, and ensure filters work. Avoid summing hull values from both triage and severity tables (fanout/duplicate totals).
8. Add a source-integrity and referral panel with quality_status and issue_codes; display `INTERNAL_DEMO_ONLY`, uncalibrated scores, and `UNDERWRITER_REVIEW_REQUIRED` prominently. Do not show automatic quote/bind decisions.
9. Verify the no-filter totals against the Phase 26 reconciliation JSON:
   - 7 submissions; Quote 2; Refer 4; Decline 1
   - Requested hull value: **$34,045,000** (NOT an insured value)
   - Synthetic low: **$46,243**; base: **$104,080**; high: **$208,159**
   - At least two submissions lack risk scores due to missing evidence
10. Test the slicers on submission ID and advisory label and verify drilldowns do not duplicate the seven unique IDs. Capture Desktop screenshots and record version, date, pass/fail observations in local-only evidence.
11. Do not distribute a report externally without a separate commercial-data licensing, security, underwriting model assurance and release review.

## Constraints

- The report is a synthetic research demonstration, not calibrated actuarial pricing, loss prediction, coverage advice, or underwriting approval.
- SHA-256 integrity hashes attest to equality with local snapshots only, not truth, data provenance rights or FAA verification.
- No Cirium or other proprietary records are present or licensed in these fixtures.
- Keep draft pull requests unmerged until Desktop validation is documented.
