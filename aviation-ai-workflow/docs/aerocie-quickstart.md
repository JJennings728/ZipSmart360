# AeroCIE regulatory evidence prototype — consolidated setup

This module is **separate from** the existing synthetic commercial-aviation underwriting workflow. It uses the Python standard library and the FederalRegister.gov public API. There is no AeroCIE API key, paid data dependency, or production deployment.

## Current capability

- Retrieve published Federal Register documents and current public-inspection metadata for FAA research; store dated SQLite metadata snapshots and change events. "New" means newly observed in the local database, **not** newly effective law.
- Distinguish final rules from proposed rules and public-inspection stages; show reported dates requiring verification.
- Perform preliminary model or manufacturer text screening on stored metadata.
- Retrieve FederalRegister.gov document plain text; archive byte-for-byte snapshots identified by SHA-256; flag exact text mentions and heuristic PW1100G/PW1400G family-variant *candidates* found in candidate applicability sections.
- Run a **read-only, loopback-only** local browser dashboard to browse records and view cached evidence.

## Windows PowerShell: fresh checkout

In the `aviation-ai-workflow` directory on Windows, Python 3.11+ (tested on Python 3.14):

```powershell
# No installation needed for AeroCIE's Python modules.
py -m src.aerocie.fr_collector --mode published --since 2026-10-01 --limit 10
py -m src.aerocie.fr_collector --mode document --document-number 2024-06419
py -m src.aerocie.review_queue --keyword "Pratt" --as-of 2026-10-20
py -m src.aerocie.asset_screen --model PW1100G --manufacturer "Pratt & Whitney" --as-of 2026-10-20
py -m src.aerocie.full_text_review --document-number 2024-06419 --model PW1100G --as-of 2026-10-20
py -m src.aerocie.dashboard --open
```

The dashboard runs at `http://127.0.0.1:8765/` while PowerShell is open. Press **Ctrl+C** to stop it. Full-text retrieval requires prior document metadata collection; `--offline` reuses a cached verified source-text snapshot.

### Tests

```powershell
py -m pip install pytest
py -m pytest -q
```

`pytest` is already listed in the existing underwriting demo's `requirements.txt`. All AeroCIE modules themselves use the standard library. Tests should not require API credentials or live network requests.

## Existing laptop data vs. GitHub

Your local `build/aerocie/` folder contains regulatory metadata and retrieved evidence. It is intentionally excluded by the existing root `.gitignore` rule `build/`. Pushing code does **not** upload the local database, does **not** synchronize records, and does not automatically update the running dashboard. Do not commit downloaded customer, aircraft-maintenance, or restricted-license data.

## Regulatory and security limitations

- **Not a compliance engine or FAA-approved AD applicability checker.** A model-family candidate is only a research lead. Actual applicability may depend on engine variant, installed P/N, S/N, configuration, date, exceptions, superseding directives, and maintenance records.
- FederalRegister.gov HTML/text is informational. Confirm official Federal Register PDF, current FAA DRS and incorporated-by-reference material with a qualified reviewer.
- A "rule" classification and reported effective date are **not** a legal-status guarantee. Proposed rules are not adopted AD obligations.
- The collector is **manual**, not a background monitor or scheduling service. The dashboard never updates the database automatically.
- **Do not publicly deploy or reverse-proxy** the local dashboard. No authentication or multi-tenant access control has been built.
- No commercial-space-specific monitoring, production notifications, customer exports, or enterprise audit workflows are included yet.

## Engineering priorities before commercial use

1. Design repeatable regulator-approved source validation, revision/supersession tracking, and model/part/serial screening with qualified domain review.
2. Add scheduled ingestion, error observability, and an explicit distinction between new-to-database and newly issued publications.
3. Add review acknowledgements, evidence quality indicators, date-versioned source citations, and client-controlled exports.
4. Add FAA commercial-space (14 CFR Part 450) monitoring as a **separate regulatory taxonomy**.
5. Assess access controls, customer isolation, data licensing, retention, security and independent testing before any external hosting.

For module-specific detail, see the other `docs/aerocie-*.md` files in this folder.
