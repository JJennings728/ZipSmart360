# AeroCIE-001 — Federal Register regulatory source collector

**Status:** prototype, offline unit tests; not a live regulatory alerting service.

## Why this exists

Use the **no-key, public FederalRegister.gov API** to monitor FAA publications, retrieve specific document metadata, and stage current public-inspection notices. Store immutable metadata snapshots and a separate change-event log in local SQLite. This module does **not** certify an engine's AD compliance, create a fleet-level applicability determination, or infer a rule's effective date.

## Setup (existing repository)

From `aviation-ai-workflow/` with Python 3.11+ installed:

```powershell
py -m pytest -q tests/test_fr_collector.py

# FAA publications from October 1, 2026 onward:
py -m src.aerocie.fr_collector --mode published --since 2026-10-01 --limit 25

# Narrow search to commercial space, 14 CFR Part 450:
py -m src.aerocie.fr_collector --mode published --since 2026-01-01 --cfr-part 450 --limit 25

# Retrieve a historical PW1100G/PW1400G rule by exact Federal Register number:
py -m src.aerocie.fr_collector --mode document --document-number 2024-06419

# Public inspection (NOT yet a published/effective rule):
py -m src.aerocie.fr_collector --mode inspection --limit 20

# Inspect official agency names and slugs:
py -m src.aerocie.fr_collector --mode agencies
```

On first run the program creates `build/aerocie/federal_register.sqlite3`. Keep that database local and out of Git; the default repository's `build/` outputs should not be committed.

For an alternate database path, use `--db local/path.sqlite3`. Repeated runs do not create a duplicate snapshot for unchanged metadata. The output JSON identifies new records, changed metadata, and unchanged records.

## Endpoints

| Endpoint | Usage |
| --- | --- |
| `/api/v1/documents.json` | Search FAA publications with agency, publication-date, optional CFR part or text filter |
| `/api/v1/documents/{number}.json` | Fetch a specific published rule/notices document |
| `/api/v1/public-inspection-documents.json` | Query current public inspection documents by agency |
| `/api/v1/agencies` | Resolve agency names and slugs |

The published search can return final rules, proposed rules, notices, and other types. **Document type must not be conflated with current legal effect.** Public-inspection entries are stored in an entirely different category.

## Security and accuracy

- Uses the standard-library HTTPS client with safe relative API paths; no credentials.
- Date extraction is unmodified: if `effective_on` is missing or uncertain, report it as missing.
- Saves hashes of normalized metadata and a diff excerpt of any changed metadata. **Does not download or diff full rule text.**
- A changed API record is **not** by itself a new rule or amendment. Amendments and corrections often have separate FR document numbers.
- No asset-level or operator-specific applicability determination is made.
- Official legally operative documents must be verified through the official Federal Register PDF on GovInfo and current FAA Dynamic Regulatory System when appropriate.
- Keep retrieved source terms, provenance, data retention, request volumes, and rate limiting under review before production deployment.
- No external customer records or NASA/SWIM credentials belong in this prototype.

## Next engineering milestones

1. Official-text acquisition with GovInfo/FAA source verification and content versioning.
2. Domain-specific candidate matching for airworthiness, operations, and 14 CFR Part 450 — all flagged for human review.
3. Structured compliance-review tasks and audit-ready HTML report.
4. FAA DRS evidence-check links; optional eCFR official regulatory text lookup.
5. Monitoring, error alerts, tests against known historical corrections, and lawful terms/usage review.

**Sources:** [Federal Register API](https://www.federalregister.gov/developers/documentation/api/v1), [Developer Resources](https://www.federalregister.gov/reader-aids/developer-resources/rest-api), [Official Federal Register on GovInfo](https://www.govinfo.gov/app/collection/FR), [FAA DRS](https://drs.faa.gov/).
