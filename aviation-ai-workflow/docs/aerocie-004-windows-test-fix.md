# AeroCIE-004 — Windows SQLite test cleanup fix

**Issue:** `PermissionError: [WinError 32]` while `tempfile.TemporaryDirectory` removes the SQLite fixture `federal_register.sqlite3` during 15 AeroCIE full-text tests on Windows / Python 3.14.

**Root cause:** The tests used `with sqlite3.connect(db) as conn:`, which manages a transaction but does **not** close the SQLite connection. The still-open handle blocks Windows from deleting the temporary file.

**Resolution:** In `tests/test_aerocie_full_text_review.py`, wrap both SQLite fixture connections in `contextlib.closing`, while retaining the `conn` transaction context (`with closing(sqlite3.connect(...)) as conn, conn:`). This commits on successful setup and closes promptly before temporary directory cleanup.

**Modified production files:** None. **Modified database files:** None. The ZIP includes only the full-text test and this explanatory note; it is safe to merge into the existing ZipSmart360 checkout without replacing existing AeroCIE source or SQLite data.

**Offline checks in development environment:** 40 tests passed, including 15 full-text tests, 10 model-screen tests, 7 review-queue tests and 8 collector tests. The fix has not yet been verified on the user's Windows PC; local connection and live full-text fetch must be tested separately.

## Windows PowerShell

From an existing shell, run one command at a time:

```powershell
Expand-Archive -Path "$HOME\Downloads\AeroCIE_004_Windows_Test_Fix.zip" -DestinationPath "$HOME\Documents\SRP\ZipSmart360-main" -Force
cd "$HOME\Documents\SRP\ZipSmart360-main\aviation-ai-workflow"
py -m unittest tests.test_aerocie_full_text_review -v
```

Expected ending: `Ran 15 tests ... OK`. Then perform the previously pending *live* fetch separately:

```powershell
py -m src.aerocie.full_text_review --document-number 2024-06419 --model PW1100G --as-of 2026-10-20
```

The full-text module remains a research triage tool, not a definitive asset applicability or airworthiness compliance determination.
