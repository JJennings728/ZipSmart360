# AeroCIE-005 — Local regulatory research dashboard

**Purpose:** Browser-based, source-linked review of an existing AeroCIE Federal Register SQLite database and already-downloaded full-text evidence. Runs on **your own computer** (127.0.0.1 only). This is an offline, read-only **research prototype**, not a hosted customer product or regulatory compliance/airworthiness certification.

## Requirements

- Your existing `aviation-ai-workflow` project, with AeroCIE-001 through AeroCIE-004b installed.
- Python 3.11+; verified with Python 3.14-compatible syntax.
- Existing `build/aerocie/federal_register.sqlite3` collector output, and optionally `build/aerocie/full_text_evidence` snapshots.
- **No pip installs, API keys, subscriptions, network calls, Flask, or Git required.** Clicking an external source link in your browser will, of course, use your internet connection.

## Windows installation

1. Download `AeroCIE_005_Local_Dashboard.zip` to `Downloads`.
2. In PowerShell, from any directory, run:

   ```powershell
   Expand-Archive -Path "$HOME\Downloads\AeroCIE_005_Local_Dashboard.zip" -DestinationPath "$HOME\Documents\SRP\ZipSmart360-main" -Force
   ```

3. In your aviation project:

   ```powershell
   cd "$HOME\Documents\SRP\ZipSmart360-main\aviation-ai-workflow"
   py -m unittest tests.test_aerocie_dashboard -v
   py -m src.aerocie.dashboard --open
   ```

4. The local page opens at **http://127.0.0.1:8765/**. Otherwise paste that address into your browser. The PowerShell window remains open while the dashboard runs. Press **Ctrl+C** to stop it.

If port 8765 is occupied:

```powershell
py -m src.aerocie.dashboard --open --port 8877
```

## How to use it

- Review and filter locally stored rule / proposed-rule / notice metadata.
- Enter `PW1100G` in the **Model mention** box, select a record, and inspect its locally archived full text. The 2024-06419 record should show candidate PW11-series variants if AeroCIE-004b previously downloaded that evidence.
- The detail view displays the saved SHA-256, retrieval time, and source links. It checks the cached text bytes against the stored hash **locally**; hash consistency is not a cryptographic signature of authenticity.
- The dashboard does not run `fr_collector` or automatically refresh regulations. To update local data, run your existing collector separately, then refresh the browser page.
- All model/variant matches are **research triage**, never a statement that a particular engine is subject to an AD, and never proof of compliance or airworthiness.

## Data & security

- It opens the existing SQLite database **read-only**. It never performs a network request, changes the database, or alters evidence files. HTML source text is escaped and government source-link domains are allowlisted.
- Binds to `127.0.0.1` only; it is inaccessible from other machines under normal networking rules. Do **not** expose or reverse-proxy this prototype on the public internet.
- Does not implement accounts, authentication, commercial audit workflows, automated regulatory-update polling, or customer access.
- The current library screen scans up to 1,000 newest snapshots and displays up to 100 rows per filtered view. It explicitly warns when more records exist.
- Missing data and no-model-mention results must **not** be interpreted as regulatory clearance.
- FederalRegister.gov plain text is an informational rendering. Verify legally operative language against official Federal Register PDFs and current FAA DRS, including corrections, supersedures, incorporation by reference, applicable models, parts and serial numbers, and compliance requirements.

## Troubleshooting

- **No database found:** Verify that you are in `aviation-ai-workflow`, or pass `--db` with the existing SQLite file path. Never create an empty replacement database just to make the dashboard start.
- **No cached full text:** Run the existing `full_text_review` command for that document separately; the dashboard only reads previously saved evidence.
- **Port in use:** Use `--port 8877` or close another dashboard instance.
- **Windows Defender prompt:** This dashboard listens only on your computer (loopback); do not enable external/public network access.
- **Test failure:** Paste the error output into the ChatGPT project conversation for diagnosis.
