# AeroCIE-034 | Integration Baseline and Open PR Dependency Map

Updated November 6, 2026. Scope: JJennings728/ZipSmart360. All open PRs below are **draft research or feature proposals** until explicitly reviewed and integrated. This register is engineering evidence, not a claim of production suitability.

## Selected integration baseline

- **Selected commercial demonstration head:** feature/aerocie-033-controlled-demo-export (PR #33, SHA 183e7b671a2b2fd61c19937a3df23d4de4c5fc9f).
- **This PR:** feature/aerocie-034-commercial-demo-acceptance, stacked on #33. Carries the internal synthetic submission brief from PR #27, adds an end-to-end integrity/regression contract, and records the release gates.
- **Do not merge any of these into main** until the remaining review gates are independently completed.

## PR dependency lanes

### Independent early prototypes
- PR #2 aviation evidence reconciliation proof of value -> main.
- PR #3 compliance evidence triage MVP -> main.
Their architecture, source and requirements must be separately reconciled; neither should be presumed in the commercial baseline.

### Research lineage (sequential, not 12 independent releases)
- #8 (009 knowledge graph) -> main
- #10 (010 corrections) -> #8
- #11 (011 effective dates) -> #10
- #12 (012 exposure map) -> #11
- #13 (013 evidence packet) -> #12
- #14 (014 review journal) -> #13
- #15 (015 offline demo) -> #14
- #16 (016 synthetic intake) -> #15
- #17 (017 pilot readiness) -> #16
- #18 (018 workbench) -> #17
- #19 (019 model assurance) -> #18
- #20 (020 underwriting sensitivity) -> #19
- #21 (021 evidence quality) -> #20
- #22 (025 SQLite close) -> #21
- #23 (026 export reconciliation) -> #22
- #24 (027 Power BI measures) -> #23

### Commercial dashboard and defense-prime sequence
- #26 (028 commercial dashboard) -> main. Contains substantial historical research and Power BI changes consolidated as a distinct dashboard branch.
- #27 (synthetic submission brief) -> #26. Its file src/aerocie/submission_brief.py is intentionally carried into this PR, **without merging its PR**.
- #28 (synthetic engine/fuel scenario) -> #26
- #29 (synthetic prime supplier screen and CSV adapters from merged PR #30) -> #28
- #31 (source reconciliation) -> #29
- #32 (research reviewer journal) -> #31
- #33 (gated synthetic internal export) -> #32
- #34 (cross-feature acceptance and case brief) -> #33

PR #30 was merged into PR #29's **development branch**, not main. It is not among the open PRs.

## Divergence and collision risk

On November 6, GitHub compare reported:
- #24's feature/aerocie-027-powerbi-measures vs #26's feature/aerocie-028-commercial-dashboard as DIVERGED (the dashboard branch was 13 commits ahead and 4 behind the earlier branch).
- #26 vs #33 as an ancestor-to-descendant relationship (33 was 22 commits ahead and 0 behind).
- main vs #33 as DIVERGED (33 was 81 commits ahead and 11 behind main at that point).

**Do not manually combine the two competing PBIR directories or automatically merge #24 followed by #26.** Both alter the Power BI report/semantic model. First compare the exact TMDL relationships, measures, PBIR visual bindings, data types and both report sets in a disposable staging checkout. Keep the tested #26 report as the proposed canonical demonstration unless explicit reviewer acceptance establishes a different version.

## Verified Windows baseline on HPJJ

At SHA 183e7b671a2b2fd61c19937a3df23d4de4c5fc9f, a disposable checkout ran without installing packages:
- Synthetic SQLite create and Power BI CSV export: PASS.
- Export reconciliation: PASS; 7 unique submissions; Quote=2, Refer=4, Decline=1; requested hull=$34,045,000; Low/Base/High synthetic sensitivities $46,243/$104,080/$208,159.
- Ten CSV SHA-256 manifest entries: verified.
- Underwriting source/evidence quality gate: INTERNAL_DEMO_ONLY; external_release_authorized=false.
- PBIR schema validator: PASS.
- All 32 existing test_aerocie_*.py files: **392 tests and 85 subtests passed on Python 3.14**.

These are synthetic, assumption-based research outcomes, not insurance coverage decisions, actuarial forecasts, validated regulatory source facts or real engine operating economics.

## Unclosed release gates

1. Run this PR's new test_aerocie_commercial_handoff.py and the full CI matrix on its exact head.
2. Power BI Desktop: verify genuine PBIP import, TMDL parsing, DAX evaluation, all seven CSV refreshes, row relationships, interactive slicers, page navigation, Montserrat fallback and all four pages visually. Windows CLI/schema testing is NOT Power BI Desktop rendering. No evidence is currently recorded of a passed Desktop acceptance.
3. Establish review of conflicting features relative to current main (main had 11 commits not in #33); prevent accidental rollback or overwrite. Do this in an isolated integration branch after separate authorization.
4. Integrate approved data contract: real FAA/NTSB/Cirium/OEM data only with independent permissions and compliance review; never load FCI, CUI, export-controlled, classified, personal or proprietary data into this public repo.
5. Customer/underwriter decision workflows: authenticated identity, independent reviewer signoff, permissions, data segregation, logging, retention, release policy, insurance/E&O and licensing evaluation.
6. Keep all reports watermarked internal synthetic, and never claim FAA approval, certified MOSA, CMMC, loss forecasts or live supplier authentication.

## Suggested integration sequencing

A. Preserve the research branch and the commercial branch as historically reviewable.
B. Validate #34 as an internal complete synthetic case study.
C. Review source and report differences between #24 and #26 with the Power BI Desktop operator.
D. Prepare a new isolated merge-proposal branch from current main; resolve specific upstream changes, run the whole test suite, inspect the report, seek approval, then integrate in intentionally small stages. Do not merge open PRs simply because tests are green.
E. Once validated and authorized, publish only a truthful demonstration description to SRP's customer-facing website—not the internal report or data fixtures.
