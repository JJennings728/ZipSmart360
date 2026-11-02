# AeroCIE-017 | Phase 21 report presentation and pilot readiness

**Status:** Draft internal demonstration only. This is a pre-commercial pilot workstream and is **not** authorization to release a customer report, open a production intake portal, or represent FAA certification.

## Delivered in Phase 21

- `src/aerocie/pilot_report.py` — static, printable, scriptless HTML intelligence briefing built on the checksum-validated AeroCIE-013 packet, AeroCIE-014 journal and synthetic-only AeroCIE-016 intake.
- `tests/test_aerocie_pilot_report.py` — regression coverage for synthetic-only intake, evidence integrity, HTML escaping, no reviewer PII, unchanged input files, no overwrite, and fail-closed release status.
- `scripts/validate-phase21.ps1` — Windows-only local test and preview runner; creates a new report file in Documents, leaves the existing research databases and journal untouched.
- A printable report with executive summary, source inventory, publication chronology, proposed local correction links, eight review gates, and explicit limitations. Printing to PDF uses the browser's own **Print > Save as PDF** action; no third-party PDF service is involved.

### Windows smoke test

Checkout the draft Phase 21 branch in an unchanged Git worktree, then from `aviation-ai-workflow` run:

~~~powershell
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\validate-phase21.ps1 -Python "C:\FULL\PATH\TO\.venv\Scripts\python.exe" -OpenDemo
~~~

This only runs the named Python tests and writes a new synthetic HTML preview. It does not modify source databases or perform a deployment. Visual inspection in the user's actual browser (including print to PDF) is still required.

## Proposed $995 scope (offer concept, not an accepted contract)

**Aviation Regulatory Intelligence Review — fixed-scope desk research.**

- One agreed research question concerning one aviation facility, aircraft category, or regulatory development, with a written scope and exclusions.
- Research of up to five directly relevant primary public sources **where available**. Report every source's date, URL, version/verification limitations, and relevance. No guarantee that five qualifying sources exist.
- One short executive research brief including citations, documented changes, open questions and an actionable list of follow-up source checks.
- Optional discovery call and one clarification round, subject to written agreement. Set turnaround dates, payment and revision terms separately for each accepted engagement.

**Excluded:** legal advice, FAA or NTSB approval, compliance certification, insurance coverage or underwriting opinion, proprietary data access, real-time aviation monitoring, personal data processing, and any promise that the entire applicable regulatory universe has been found.

## Required approvals before actual customer solicitation or release

1. **Evidence accuracy:** Independently inspect authoritative sources, obtain citations and amendment history, correct incomplete or speculative claims. Local SHA hashes alone are insufficient.
2. **Regulatory review:** Determine what the particular factual subject actually is; confirm applicability with qualified review, or preserve an explicit NOT_DETERMINED status. The seven skipped AeroCIE human-review checks must not be marked complete by automated tests.
3. **Data handling:** Agree a lawful collection purpose and minimal fields, access restrictions, encryption, secure disposal, retention, and incident response. The present intake schema is NOT a privacy filter and cannot accept real client records.
4. **Legal/commercial:** Confirm authorization, contractual terms, permitted data sources, E&O coverage as applicable, limitations of liability, payment and refund terms, and right to use material in marketing.
5. **Security:** Code and dependency review, malicious-input tests, protections against file disclosure, validation that publication links resolve, and review of code-generation/output paths.
6. **Visual and accessibility QA:** Review desktop and mobile appearance, print output, page breaks, contrast and accessibility of tables and links in a real browser.
7. **Business validation:** Interview prospective aviation insurance producers or underwriting teams about their actual evidence and reporting workflows. $995 is a proposed price, not evidence of willingness to pay.
8. **Explicit release decision:** Only after the above, approve a separate controlled delivery mechanism. Keep the current `external_release_authorized=false` hard gate in the prototype.

## Internal pilot acceptance criteria

- All Phase 21 focused and AeroCIE regression tests pass on Windows.
- Generated HTML displays correct eight check states with no reviewer names or private notes.
- Fictional source links are disabled; valid Federal Register URLs in the real internal packet are marked as **format checked, not source authenticated**.
- No real client details are saved, no production site is exposed, and source databases are preserved.
- The report can be printed to PDF and visually reviewed without clipping or data loss.
- Full stack dependencies remain in **draft PRs**; code may still need independent review before merge.

## Source/code provenance

Stacked after AeroCIE-016 PR #16. No merge, deployment, purchase, or external sharing is part of this phase.
