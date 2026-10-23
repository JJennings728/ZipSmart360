# AeroCIE-008 | Source-linked research candidate register

**Status: local prototype | NOT a compliance determination | no customer release.**

This module introduces a **candidate research register** in the existing AeroCIE project. It creates a local record of why a Federal Register publication deserves qualified attention, its assigned internal researcher, and the research workflow history. It does not infer legal obligations from text, assert that a rule applies to an aircraft or organization, or authorize client work.

## What exists

- Create a manually described *research question* against an **existing published** Federal Register snapshot, using its exact saved SHA-256 fingerprint.
- Record an internal research owner and voluntary review target date. **This is not a statutory deadline.**
- Record local research statuses and an event history in a separate SQLite database; the federal source collector database is read-only to AeroCIE-008.
- List all candidates, always showing `compliance_status: NOT_DETERMINED` and `external_release_authorized: false`.
- Flag source changes or missing original source snapshots for fresh review.
- Zero added pip packages, API accounts, cloud hosting, or customer data.

## Windows PowerShell from existing project folder

```powershell
cd "$HOME\Documents\SRP\ZipSmart360-main\aviation-ai-workflow"
py -m unittest tests.test_aerocie_obligation_register -v
py -m src.aerocie.obligation_register init

# First collect the FAA document into the existing local source database.
py -m src.aerocie.fr_collector --mode document --document-number 2024-06419

# This creates a research question, NOT an actual regulatory obligation.
py -m src.aerocie.obligation_register add-from-faa --document-number 2024-06419 --question "Determine whether this publication is relevant to our research scope." --actor "Research analyst" --owner "SRP research" --review-by 2026-11-01

py -m src.aerocie.obligation_register list
# Use the candidate ID shown above:
# py -m src.aerocie.obligation_register status --id <id> --state RESEARCH_HOLD --actor "Research analyst" --notes "Need current FAA DRS and supersession verification."
# py -m src.aerocie.obligation_register history --id <id>
```

The collector's Federal Register API is public. There is **no new API key** needed for this module.

## Explicit boundaries

1. `RESEARCH_CANDIDATE`, `UNDER_RESEARCH_REVIEW`, `RESEARCH_HOLD`, and `ARCHIVED_RESEARCH_ONLY` are **internal process states**, never legal/compliance outcomes.
2. Source receipt fingerprints are integrity references, not authenticated or tamper-proof organizational signatures. SQLite is not an enterprise audit vault.
3. Candidate entries are manual; no LLM extraction, entitlement logic, part-number or serial-number compliance verification, licensing automation, real-time feeds, authentication or multi-tenancy is included.
4. Never enter passwords, personal financial data, controlled technical information, classified data, or unapproved customer records.
5. Before customer release, verify governing source text, FAA DRS, revisions, applicability, evidence, access controls, data rights and qualified approval.
6. The `build/` folder stays untracked per repository rules; do not publish local databases.
