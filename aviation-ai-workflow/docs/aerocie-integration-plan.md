# AeroCIE | API and PowerShell implementation plan

## Current, already integrated
- **FederalRegister.gov API v1**: live published/public-inspection metadata research through existing `src.aerocie.fr_collector`; no key required for basic queries.
  Documentation: https://www.federalregister.gov/developers/documentation/api/v1
- **FAA Dynamic Regulatory System (DRS)**: official current FAA source cross-check. Human source validation; do not claim a stable sanctioned API without documentation. https://drs.faa.gov/
- **SQLite 3**: built into Python standard library; separate local source and candidate registers. **Not** hosted multi-tenant infrastructure.
- **GitHub**: change control and tests in existing repository; no secrets or local `build` data in commits.

## Optional integrations, not required for AeroCIE-008
- **OpenAI Responses API**: model-assisted candidate extraction and structured JSON with strict schemas; optional *future* AeroCIE-010 feature requiring a paid API key and test coverage. https://developers.openai.com/api/reference/responses/overview
- **NTSB CAROL Enterprise API**: aviation incident/case research, not regulatory obligations or compliance determinations. Obtain and verify authorization/terms in the NTSB developer portal.
- **NASA EONET API v3**: natural-event contextual research, not FAA compliance. Public events API https://eonet.gsfc.nasa.gov/api/v3/events
- **Regulations.gov API v4**: rulemaking docket/document context, separate from Federal Register published legal text; get an api.data.gov key if integration is justified. https://open.gsa.gov/api/regulationsgov/
- **FAA SWIM SFDPS**: separate entitlement, contract terms, and operational data scope; **not** a source of regulatory obligations and **not needed** to build AeroCIE-008.
- **SAM.gov Entity API**: government vendor registration checks, not aviation compliance; only add if procurement workflow becomes customer-validated.

## Zero-budget Windows workflow

```powershell
# Update your EXISTING checked-out repository. Do not clone a new SRP project.
cd "$HOME\Documents\SRP\ZipSmart360-main"
git status
git fetch origin
# After reviewing and merging an approved PR, update your local main:
# git checkout main
# git pull --ff-only origin main

cd aviation-ai-workflow
py --version
py -m unittest tests.test_aerocie_obligation_register -v
py -m src.aerocie.obligation_register init
py -m src.aerocie.obligation_register list

# Existing Federal Register monitor: manual execution, internet required
py -m src.aerocie.monitor --lookback-days 7 --limit 100

# Public API smoke test with no key:
Invoke-RestMethod -Uri "https://www.federalregister.gov/api/v1/documents.json?per_page=1" | Select-Object -ExpandProperty count
```

Only use locally staged and synthetic information until legal, IP, privacy, and security checks permit customer data. Never paste API keys into chat, commits, scripts, or browser code. Use environment variables and a secret manager when a paid integration is added.

## Implementation order
1. AeroCIE-008 | Source-linked candidate research register and tests.
2. AeroCIE-009 | Internal research evidence references and gap-triage logic.
3. AeroCIE-010 | Optional bounded AI extraction with source links and schema validation.
4. AeroCIE-011 | Tasks, reviewer roles and workflow permissions.
5. AeroCIE-012 | Access-controlled design-partner pilot after independent testing.

No customer-facing marketing should imply these milestones are implemented before corresponding code and validation exist.
