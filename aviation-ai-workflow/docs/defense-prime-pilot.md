# AeroCIE Defense-Prime Pilot | Internal Synthetic v1

**Stage:** Design validation, not production. All fixtures are fictional and `PUBLIC_SYNTHETIC_ONLY`; no customer data, CUI, FCI, classified, export-controlled or licensed provider records. No network or LLM calls. `external_release_authorized=false` is mandatory.

## Objective and reusable modules

1. **541511 | Software and AI workflows:** a deterministic evidence-fingerprint gate and versioned JSON input/output. An AI connector is **not** enabled; any future model/provider integration needs approved data handling, access controls, review, logging, and independent validation.
2. **541512 | Data integration:** schema-stable JSON input and portable JSON/SQLite outputs. This demonstrates adapter separation, **not verified MOSA conformity**. Contract-specific standards, replacement tests, interface documentation, security and portability validation remain required.
3. **541690 / 541715 | Aerospace risk intelligence:** fictional supplier/component dependency screening, unmitigated lead-time deltas, assumed critical-path flags and source-linked review list. **Not** a schedule forecast, verified sub-tier traceability, actuarial assessment, manufacturing engineering determination or procurement recommendation.

## Use

From `aviation-ai-workflow` (Python 3.11+):

```powershell
$env:PYTHONUTF8="1"
python -m unittest tests.test_aerocie_prime_pilot -v
python -m src.aerocie.prime_pilot --input sample-data/prime_scrm_synthetic.json --out build/prime-screen.json --db build/prime-screen.sqlite3
```

The CLI refuses to overwrite existing reports or databases. Remove or rename test output **only after reviewing its contents** before rerunning. No external calls are made.

## JSON interface

Input v1:

- `schema`: `SRP-PRIME-SCRM-v1`
- `data_classification`: exactly `PUBLIC_SYNTHETIC_ONLY`
- `external_release_authorized`: exactly `false`
- `program`: nonempty label
- `evidence`: array of `evidence_id`, `text`, SHA-256 over UTF-8 text (`sha256`), and `synthetic:true`
- `suppliers`: array of `supplier_id`, `name`
- `components`: array of `component_id`, `supplier_id`, `evidence_id`, nonnegative integer `baseline_lead_days`, `scenario_lead_days`, Boolean `critical_path_assumed` and `single_source_assumed`

Output v1 provides the input digest, computed per-component lead-time differences, evidence references, review flags, a non-forecast summary, limitations and report digest. JSON fields are explicit, deterministic, and suitable for future *documented* adapter implementations. Evidence digests detect local modifications; they do not authenticate sources.

SQLite contains `reports` and `component_screen` tables linked by a report SHA-256. Local-only, basic relational persistence does not by itself provide encryption, multitenancy, authenticated access, authorization, audit-grade tamper resistance or CMMC controls. No actual supplier API or ERP integration is connected.

## Acceptance before pilot expansion

- All test cases pass, including evidence tamper, classification blocking, duplicate IDs, unknown references, malformed numeric inputs, and no-overwrite behavior.
- Validate report output with at least two independently constructed synthetic fixtures and reconcile the same results against a manually reviewed calculation.
- Document a program-specific interface specification, identity boundary, data ownership, licensing, retention, backup, encryption, vulnerability review, and integration approvals.
- For actual program work, determine contract clauses, CUI/FCI applicability, export-control restrictions and applicable NIST/CMMC obligations; keep live data out until controls are assessed and authorized.
- Independently map a real deployment against applicable MOSA interface and standards requirements and verify swapping an adapter without changing the analytical core.

## Regulatory guardrails (verify against each solicitation)

- [10 U.S.C. 4401](https://uscode.house.gov/us/usc/119-124/t10/s4401/) defines MOSA as a business and technical strategy, including interface verification; publishing JSON does not establish MOSA compliance.
- [DoD CMMC portal](https://dodcio.defense.gov/cmmc/About/) explains the phased assessment framework. As of November 2026, DoD announced a pause of the planned Phase II rollout; Phase I obligations and contractual security requirements remain.
- [NIST SP 800-171 Revision 3](https://csrc.nist.gov/pubs/sp/800/171/r3/final) is published, but current CMMC assessments may still use the revision specified in the applicable program rule/contract. Do not infer a required revision from this demo.

## Commercial scope for first prime pilot

A fixed-scope, **30–60-day target only if requirements and authorized non-sensitive data are available**: discovery, source contract, synthetic connector proof, dependency-risk screen, human-reviewed report, reproducible acceptance tests. Program schedule slip and cost forecasts require a separately validated model and customer-supplied network logic. Do not promise an OTA contract or CMMC certification.
