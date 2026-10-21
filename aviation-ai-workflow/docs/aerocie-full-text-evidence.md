# AeroCIE-004 — Federal Register full-text evidence & candidate model screening

**Status:** experimental aviation compliance *research triage*, not authoritative applicability assessment or certified maintenance/regulatory compliance. No paid API, Python dependencies, or new Git repository required.

## What this does

1. Reads a **previously collected published** Federal Register record from the existing read-only SQLite database.
2. Downloads the corresponding **FederalRegister.gov plain-text rendering** over HTTPS from the domain and document path validated against local metadata. No arbitrary URLs or redirects are followed.
3. Saves the exact original response bytes under a SHA-256 content-addressed filename with a JSON source/timestamp/provenance manifest, preserving previous versions.
4. Screens for exact model token mentions and indicates whether the mention lies inside a **candidate** `(c) Applicability` heading section. Displays short evidence excerpts and a citation link.
5. Flags every result for manual review; never declares an aircraft/engine affected, compliant, noncompliant, or clear.

## Install

Save `AeroCIE_004_Full_Text_Evidence.zip` to your Downloads folder. In PowerShell, run:

```powershell
Expand-Archive -Path "$HOME\Downloads\AeroCIE_004_Full_Text_Evidence.zip" -DestinationPath "$HOME\Documents\SRP\ZipSmart360-main" -Force
cd "$HOME\Documents\SRP\ZipSmart360-main\aviation-ai-workflow"
py -m unittest tests.test_aerocie_full_text_review -v
```

## Live evidence test

The historical document `2024-06419` was ingested in AeroCIE-001, so use that local document:

```powershell
py -m src.aerocie.full_text_review --document-number 2024-06419 --model PW1100G --as-of 2026-10-20
```

Look for the `sha256`, `evidence_text_path`, `official_pdf_url_for_manual_verification`, and `sample_evidence` fields. For a *second run without network*, add `--offline`. Full-text retrieval requires Internet access the first time.

Test a second document (already ingested) with a different model, e.g. `--document-number 2026-21290 --model PW1100G`; a no-match result is **not** evidence the model is unaffected.

### Important constraints

- **Not full FAA DRS status verification.** The FAA DRS is still required to check current ADs, corrections, superseding directives, effective and compliance dates.
- **Not authoritative legal source.** FederalRegister.gov plain text is an informational rendering. Compare it with the official Federal Register PDF linked in the report and the incorporated technical/maintenance instructions.
- **Not a definitive Applicability parser.** The script locates heading-like candidate regions and exact model mentions; formatting variations, exceptions, negative assertions, series/variant naming, and referenced service documents require a qualified analyst.
- **No compliance inference.** Positive mention, negative mention, or no mention never establishes legal applicability, airworthiness or clearance. Serial numbers, parts, SB revisions, operator records and exclusions need separate independent checks.
- **No silent overwrites.** An identical downloaded body is recognized using its SHA-256; changed bytes are archived as a second snapshot. A changed rendering does **not** automatically mean a regulatory amendment.
- **No extra cost.** All functionality uses Python's standard library. Local disk storage grows with archived texts; no background scheduling is configured.

## Optional reproducible export

```powershell
py -m src.aerocie.full_text_review --document-number 2024-06419 --model PW1100G --offline --report-out build/aerocie/reports/PW1100G_2024-06419.json
```

The report describes the **local evidence and research screen only**, not a certified legal, engineering, or airworthiness opinion.
