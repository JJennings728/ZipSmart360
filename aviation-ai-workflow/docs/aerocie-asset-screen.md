# AeroCIE-003 — Aircraft and engine model mention screen

**Status:** prototype; metadata-only screening, not asset applicability or a compliance opinion.

This is an **additive update** to the existing AeroCIE-001 collector and AeroCIE-002 review queue. It adds just one read-only Python module and its tests. The ZIP doesn't include or overwrite your SQLite database.

## Installation on Windows

1. Save `AeroCIE_003_Asset_Metadata_Screen.zip` to Downloads.
2. Extract it into `$HOME\Documents\SRP\ZipSmart360-main` using PowerShell:

   ```powershell
   Expand-Archive -Path "$HOME\Downloads\AeroCIE_003_Asset_Metadata_Screen.zip" -DestinationPath "$HOME\Documents\SRP\ZipSmart360-main" -Force
   ```
3. From the existing project folder run:

   ```powershell
   cd "$HOME\Documents\SRP\ZipSmart360-main\aviation-ai-workflow"
   py -m unittest tests.test_aerocie_asset_screen -v
   ```
4. Run the actual local database screen:

   ```powershell
   py -m src.aerocie.asset_screen --model PW1100G --manufacturer "Pratt & Whitney" --as-of 2026-10-20
   ```

## Interpreting results

`model_mentions` are **explicit textual mentions** of the specified model in locally stored Federal Register **title, abstract, or action metadata**. They are not evidence that a particular serial-numbered engine is affected.

`manufacturer_context_only` are lower-confidence research leads when the manufacturer is mentioned but the requested model isn't. Do **not** present them as asset matches; the October 2026 Pratt & Whitney proposed rule is an example.

**No match does not mean no applicable AD exists.** This is not a full-text or comprehensive AD lookup; many Federal Register abstracts and document titles omit model designations, even when the rule's body includes them. Check current FAA DRS, official rule text, superseding ADs, model variants, serials, parts, exclusions, and compliance records before any asset determination. Proposed rules, finalized rules, and their effective dates are distinct.

`scan_truncated` means the data query hit the user-selected scan limit; increase `--scan-limit` (up to 5000) or narrow the stored dataset. This tool does not fetch new documents. To add documents, run the AeroCIE-001 collector again. Manufacturer aliases are explicit, not automatically inferred:

```powershell
py -m src.aerocie.asset_screen --model PW1100G --manufacturer "Pratt & Whitney" --manufacturer-alias "Pratt and Whitney" --as-of 2026-10-20
```

The operation opens SQLite with `mode=ro` and closes its connection explicitly, avoiding Windows file locking.

## Future development

AeroCIE-004 should ingest **full official rule text** with provenance, verify current DRS status, extract true applicability sections and part/serial exceptions, and keep human review mandatory. Never claim automatic compliance verification.
