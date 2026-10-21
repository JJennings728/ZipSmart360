# AeroCIE-002 — FAA regulatory publication review queue

This is a **read-only**, zero-dependency extension to the already working AeroCIE Federal Register collector.

It reads the SQLite database created by `fr_collector` and classifies regulatory *publication categories*:

- `PRORULE` = a proposed rule, not a new binding AD from the proposal itself;
- `RULE` = a published rule; current legal force and applicability must still be checked;
- `NOTICE` = a notice; review relevance;
- `public_inspection` = pre-publication material, tracked separately.

It also identifies whether a **reported** rule effective date lies after an explicitly selected as-of date. A missing date is not proof that the rule is ineffective. It does **not** extract true compliance deadlines, establish airworthiness, verify engine serial numbers, or replace FAA DRS.

## Install

Extract this package into the existing ZipSmart360 project root. Keep the prior `fr_collector.py` and the local SQLite DB in place. This package adds only `review_queue.py`, a test file, and this documentation. It makes no changes to the original collector.

## Use in PowerShell

```powershell
cd "$HOME\Documents\SRP\ZipSmart360-main\aviation-ai-workflow"
py -m unittest tests.test_fr_review_queue -v
py -m src.aerocie.review_queue --keyword "Pratt" --as-of 2026-10-20
py -m src.aerocie.review_queue --format csv --out build/aerocie/regulatory_review.csv
```

When viewing CSV, **all entries require human review** and no row is a verified engine/aircraft compliance conclusion. `reported_effective_on` is metadata from the Federal Register, and may not contain every compliance condition or deadline. FAA DRS and incorporated service information must be reviewed for an asset-level determination.

## Windows SQLite file-handle compatibility fix (2026-10-20)

The first review-queue ZIP used `with sqlite3.connect(...)` in the test fixture
and the queue reader. Python's SQLite connection context manager commits or
rolls back a transaction, but **does not close the connection**. On Windows,
`TemporaryDirectory` cannot delete an open database file and raises `WinError 32`.
This update uses `contextlib.closing(...)` in the test fixture and the read-only
queue. The existing `build/aerocie/federal_register.sqlite3` is not modified.

Rerun from inside `aviation-ai-workflow`:

```powershell
py -m unittest tests.test_fr_review_queue -v
py -m src.aerocie.review_queue --keyword "Pratt" --as-of 2026-10-20
```

A successful run reports `Ran 7 tests` and `OK`.
