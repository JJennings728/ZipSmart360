# AeroCIE-018 | Local synthetic engagement workbench

**Owner:** StrategicRisk Partners LLC | **Status:** internal pilot. This feature is available in its draft branch and runs offline on the Windows workstation.

## Working product workflow

1. Open the local loopback workbench and inspect the bundled synthetic evidence state.
2. Enter a fictional organization starting with `Synthetic ` and a fictional research question; the `demo:` case and subject identifiers remain fixed.
3. Generate a report in the browser. Server reuses the Phase 20 strict intake schema, Phase 13 packet SHA-256 verifier, and Phase 21 held internal report renderer.
4. Inspect the HTML report inside the browser. Download report HTML and evidence JSON. The HTML can be opened independently and printed to PDF.
5. Use the report's unresolved review checklist to decide further research. The workbench never marks a review item complete automatically.

No database is opened for writing, and no case data is saved on the server. Temporary synthetic intake is deleted after each request. Downloads are generated in the browser using Blob objects; their final location depends on the user's browser download settings. No API key, AI API request, subscription, payment integration, telemetry, analytics, or third-party content is required.

## Run on Windows

From the `aviation-ai-workflow` directory on the Phase 22 draft branch:

```powershell
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\start-phase22-workbench.ps1 -Python "C:\FULL\PATH\TO\.venv\Scripts\python.exe"
```

After tests, browse to **http://127.0.0.1:8092/**. Leave the PowerShell session running while using the workbench; Ctrl+C ends the server. If the port is occupied, use `-Port 8093`. `-SkipTests` is available after tests have passed on that checkout.

The workbench binds to `127.0.0.1`, enforces a loopback Host header and same-origin JSON POST, returns restrictive browser headers, does not expose a file upload endpoint, and accepts a maximum 8 KB request. The browser assets are served locally. It is intended for a single operator, without authentication, collaboration, or customer data.

### Demo restrictions

- Only the approved synthetic intake fields are accepted. This is a declaration and schema check, not a guarantee that a user didn't enter real details in free text. **Do not enter real customer information.**
- The bundled source reference is fictional. Its URL is not clickable, and the report explicitly says no applicable law or compliance conclusion has been determined.
- The export remains `HOLD_FOR_HUMAN_REVIEW`, `NOT_DETERMINED`, and `external_release_authorized=false`.
- No claims of FAA approval or endorsement, insurance underwriting approval, or verified source completeness.
- Original FAA research databases and review journals are never touched by the workbench.

## Verification

- Focused tests cover the full HTTP workflow, generated HTML and JSON, mocked hostile browser origins, forbidden hosts, malformed intake, excess request size, integrity failure, escaping, and preservation.
- Run the entire AeroCIE and Federal Register regression suite before merging.
- Complete a Windows desktop, mobile-width, and PDF print visual check using the operator's real browser.

## Next engineering stages

**Phase 23:** vetted public-source demonstration with a separately documented chain of source retrieval, last-checked timestamps and linked amendments. Requires primary-source verification before describing any publication as authoritative for a customer.

**Phase 24:** real-customer intake architecture, authenticated users, encrypted case storage, role-based review, production logging, retention policy, and release controls. Requires separately approved data handling and service scope.

**Phase 25:** customer evaluation and deployment readiness with measured quality benchmarks, contract/payment workflow, operational monitoring and an approval-gated release. A working internal UI alone does not authorize deployment.
