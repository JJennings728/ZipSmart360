# AeroCIE-007 — Human source-review receipts and SRP research packet

**Purpose:** Close the gap between an automatically generated FAA research draft and a document a human has actually checked. This introduces a conservative *internal* workflow. It does **not** authorize external customer release, establish reviewer identity or qualifications, decide regulatory applicability, or provide an FAA certification.

## Key protections

- All data remains local. The Federal Register SQLite collector database is read-only to this module. Human review receipts are saved under `build/aerocie/reviewer_records/` (excluded from Git by `build/`).
- Receipts bind a named reviewer, declared role, checklist, research notes, timestamp and **exact collected metadata SHA-256 fingerprint** to one published document. Receipts are never overwritten. They are **self-attested and not digital signatures**. Editing the receipt breaks its integrity check, but someone who can edit files could create new receipts; use organizational controls before commercialization.
- If the collector saves a changed document metadata version, old receipt(s) cannot verify the new version; another review is required.
- `source_reviewed_research_only` requires three explicit human-confirmed checks: Federal Register text/PDF, current FAA Dynamic Regulatory System (DRS), and supersession/amendments. Checking these boxes is **not** a substitute for actual qualified review.
- Public-inspection records remain unreviewed research-stage items; this workflow does not apply published-source signoff to public-inspection versions.
- Reports remain **INTERNAL DRAFT** and **NOT AUTOMATICALLY APPROVED FOR CLIENT DISTRIBUTION**, even if all records have source-review receipts. Customer release, asset/part serial checks, contractual scope, licensing and relevant professional review are separate gates.

## Test and print a branded internal packet first

From `C:\Users\James\Documents\SRP\ZipSmart360-main\aviation-ai-workflow` in PowerShell:

```powershell
py -m unittest tests.test_aerocie_reviewer_packet -v
py -m src.aerocie.reviewer_packet packet --keyword "Pratt" --out "build/aerocie/reports/srp-pratt-internal-draft.html"
Start-Process "build/aerocie/reports/srp-pratt-internal-draft.html"
```

Use the browser **Print → Save as PDF** for a local copy. An unreviewed packet will explicitly show unreviewed records. Do not distribute to customers yet.

## Optional: record an actual review after checking sources

For records needing more research, a person reviewing the case can register a **hold** (this does not imply sources were checked):

```powershell
py -m src.aerocie.reviewer_packet record --document-number 2026-21290 --reviewer "Your actual name" --reviewer-role "Research analyst" --notes "Further official source, DRS, and supersession checks are still required." --disposition hold_for_review
```

Only after a **qualified** person genuinely performs all three independent source checks, they may designate it source-reviewed, by adding `--disposition source_reviewed_research_only --federal-register-checked --faa-drs-checked --supersession-checked` to a command with authentic name/role/notes. **Never check boxes you have not verified**, and do not use a test reviewer identity for real records.

After registering a receipt, rerun `packet` to inspect the new status. Avoid claiming current FAA AD status or affected aircraft/engine applicability unless separately verified against current DRS and actual asset records. Code uses only the Python standard library and no paid tools.

## Remaining before paid delivery

1. Authenticated signoff, review permission controls and change history for receipts.
2. Coverage-completeness monitoring and missed-day catch-up, including explicit caveats for 500-result caps.
3. Commercial review of source licensing, contract/terms and deliverable claims.
4. Source-verified sample report based on a clearly delimited research scope; identify and document a prospective buyer's problem before building more features.
5. No hosted deployment until access controls, privacy and hardening are implemented.
