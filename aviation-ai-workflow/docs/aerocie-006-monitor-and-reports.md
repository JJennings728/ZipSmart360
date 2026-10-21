# AeroCIE-006 — Repeat Monitoring & Source-Linked Review Drafts

## Scope and assurance

This adds two independent, **local-only** tools to the existing `aviation-ai-workflow`:

- `src.aerocie.monitor` reuses the Federal Register API collector and the same SQLite snapshot/change-event database. It distinguishes first-time collection, repeated metadata and metadata changes. It does **not** equate an event with a new legal obligation.
- `src.aerocie.report` exports a self-contained, print-ready HTML **DRAFT** from the stored local records. It includes source links, publication type, reported dates, limitations and a space for qualified review. Print to PDF from the browser after source verification; no paid PDF tools needed.

**Neither module performs automatic asset compliance determinations, legal advice, or client approval.** Unreviewed drafts must not be sent to customers. See the existing `docs/aerocie-quickstart.md` and governance documentation. This code does not run on SRiskPartners.com and does not authenticate users.

## One-time installation / live smoke test (after merging and obtaining updated code)

Run from `aviation-ai-workflow` in PowerShell:

```powershell
py -m unittest tests.test_aerocie_monitor_report -v
py -m src.aerocie.monitor --lookback-days 7 --limit 500
py -m src.aerocie.report --keyword "Pratt" --out "build/aerocie/reports/pratt-review-draft.html"
Start-Process "build/aerocie/reports/pratt-review-draft.html"
```

The monitor stores *run-specific* `.json` and `.html` output under `build/aerocie/reports/`, while retaining prior snapshots in `build/aerocie/federal_register.sqlite3`. The repository's existing root `.gitignore` excludes `build/`, so **no local evidence or client documents are committed to public GitHub**. Source links target known `.gov` / Federal Register domains only. Full-text and applicability evidence must still be assessed using prior AeroCIE modules.

**First-run baseline:** With an empty database, discovered publications are marked `new_to_database`; this means only newly observed *locally*, not newly issued. Subsequent matching records are unchanged. On fetch error, the monitor exits nonzero and does not mark the scan as complete. When the search reaches its `--limit`, the tool explicitly marks the scan incomplete and exits code 2. Date overlap limits omissions but does not guarantee total discovery.

**Optional public inspection:** Add `--include-inspection` to check the API's public-inspection category separately. The initial scheduled-run example below checks only *published* FAA documents until that optional feed is live validated.

## Optional daily Windows Task Scheduler setup

This registration is **not** performed by merging the pull request. When ready, from your existing project folder, choose your preferred local clock time explicitly, e.g. `09:00`:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\scripts\aerocie-register-daily.ps1" -At "09:00"
```

This registers **SRP AeroCIE FAA Monitor** using the currently signed-in Windows account (not SYSTEM), running the local script at the selected local time. The scheduled task runs **only while the account is signed in**. Your computer must be on and connected. Depending on Windows account policy, Task Scheduler may require permission adjustments. This creates **no server/cloud automation**, does not send alerts or email, and does not upload data. It may be stopped or deleted using Windows Task Scheduler. Logs are stored under `build/aerocie/logs/`. The task does not execute without you explicitly registering it.

Test the runner manually *before* scheduling:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\scripts\aerocie-run-daily.ps1"
```

## Risk and limitations

- No guarantee every relevant rule is found. The monitor searches by FAA agency and rolling publication date, with up to 500 results per run; cap detection is a warning, not a pagination guarantee.
- Publication dates and reported effective dates are distinct. Publication and initial matching do not establish applicability.
- The first baseline run is not a legal update alert. There are no outbound notifications, webhook calls, client dashboards, or continuous background services.
- No copy of the authoritative legal text or incorporated service bulletins is provided by the HTML report. Users must verify official PDF and FAA DRS; assess revisions, applicability clauses, part/serial ranges, exceptions and deadlines.
- The HTML report is a **review packet**, not final client work. There is no reviewer-signoff database or approval workflow yet.
- Avoid using real client data in this publicly accessible code repository; the existing local dashboard is unauthenticated and must not be published on the internet.

## Next milestones

1. Improve complete-coverage detection, missed-run catch-up and monitoring audit records.
2. Build a qualified-review/approval queue before commercial deliverable release.
3. Add FAA commercial-space rules (Title 14 Part 450), tracked separately from aircraft ADs.
4. Design access controls and licensing rules before any hosted/SaaS publication.
