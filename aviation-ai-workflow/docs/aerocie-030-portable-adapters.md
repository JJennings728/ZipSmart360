# AeroCIE-030 | Interchangeable Offline Source Adapters

**Development state:** Draft integration proof. No live API connections or customer data. This work extends [the synthetic defense-prime screening pilot](defense-prime-pilot.md), stacked on PR #29.

## Why this exists

One aerospace risk model should accept data through different documented interfaces without changing the model itself. The adapter layer normalizes either local JSON or an integrity-pinned local CSV bundle into the identical `SRP-PRIME-SCRM-v1` payload expected by `src.aerocie.prime_pilot.evaluate()`.

This is **MOSA-informed modular design**, not independent verification of contractual MOSA conformance. No ERP, MBSE, PLM, DLA, FAA, NTSB, Cirium, or other external system has been integrated into this adapter. Integrations require authorized access, published schemas, provenance rules, licensing review, and test fixtures.

## Interface contracts

### Adapter A | JSON

Input: `sample-data/prime_scrm_synthetic.json`.

Run from the `aviation-ai-workflow` directory:

```powershell
$env:PYTHONUTF8 = "1"
python -m src.aerocie.prime_adapters --adapter json --source sample-data/prime_scrm_synthetic.json --out build/aerocie-030-json.json
```

### Adapter B | CSV bundle

A folder with exactly these required names:

```text
synthetic-bundle/
  manifest.json
  evidence.csv
  suppliers.csv
  components.csv
```

`manifest.json` format:

```json
{
  "bundle_schema": "SRP-SCRM-CSV-BUNDLE-v1",
  "schema": "SRP-PRIME-SCRM-v1",
  "program": "Fictional aircraft sustainment program",
  "data_classification": "PUBLIC_SYNTHETIC_ONLY",
  "external_release_authorized": false,
  "files": {
    "evidence.csv": "<SHA-256 hex digest of exact file bytes>",
    "suppliers.csv": "<SHA-256 hex digest of exact file bytes>",
    "components.csv": "<SHA-256 hex digest of exact file bytes>"
  }
}
```

CSV columns, in **exact order**:

- `evidence.csv`: `evidence_id,text,sha256,synthetic`
- `suppliers.csv`: `supplier_id,name`
- `components.csv`: `component_id,supplier_id,evidence_id,baseline_lead_days,scenario_lead_days,critical_path_assumed,single_source_assumed`

Boolean CSV fields must be lowercase `true` or `false`. Evidence `sha256` is the digest of exact UTF-8 `text` bytes, independently of the per-file pins.

Run:

```powershell
python -m src.aerocie.prime_adapters --adapter csv --source path/to/synthetic-bundle --out build/aerocie-030-csv.json
```

Each input adapter returns an identical `SRP-PRIME-SCRM-v1` research report for equivalent records, including the same canonical input fingerprint. The result exposes source-linked review flags **but explicitly does not forecast program schedule slips**.

## Security and quality gates

- Local regular files only, with symlink and size checks.
- No configurable remote addresses, network clients, API tokens, or LLM calls.
- JSON duplicate keys and nonfinite values rejected.
- CSV manifest SHA-256 file pins checked before decoding and evaluation.
- Fixed filenames and exact CSV header/column contract; extra or missing columns rejected.
- Numeric and boolean types checked explicitly; source/evidence references and synthetic-only classification enforced by downstream pilot.
- CLI output files are not overwritten.

**Not provided by this prototype:** encryption, identity verification, access authorization, endpoint hardening, secure supply-chain attestation, remote supplier authentication, actual real-world provenance, CUI authorization, approved enclave, contract-specific verification, or accreditation. The synthetic marker is a declared restriction and cannot automatically detect mislabeled sensitive content. Never supply CUI, FCI, export-controlled, classified, sensitive, or real customer data.

## Acceptance steps

```powershell
cd aviation-ai-workflow
$env:PYTHONUTF8 = "1"
python -m unittest discover -s tests -p "test_aerocie_prime_adapters.py" -v
python -m unittest discover -s tests -p "test_aerocie_prime_pilot.py" -v
```

Review the PR's GitHub CI, especially tests on the precise head SHA. Validate JSON-versus-CSV report equality using the synthetic fixture. Test a changed CSV byte against the original manifest; evaluation must fail before any report is generated. Keep the PR as draft until integration and Windows checks pass.

## Next design gates, not yet built

1. A small **public/synthetic-only** mock HTTP adapter or documented on-premises file-drop contract, with explicit ingress authorization and source schema.
2. Schema version migration and source-reconciliation ledger, including completeness, duplicate keys, timestamps, license metadata, and corrections.
3. An editable supply-chain dependency graph with supported lead-time scenarios and separately validated schedule logic.
4. Human-reviewed risk packets and exportable records for technical discovery.

Do not market this as a production connector, proven air-gap deployment, completed aerospace integration, full MOSA compliance, or CMMC certification.
