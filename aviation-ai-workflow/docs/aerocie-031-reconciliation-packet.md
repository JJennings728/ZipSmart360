# AeroCIE-031 | Evidence Reconciliation and Human Review Packet

**Status:** Internal synthetic demonstration; draft only. Not a government or supplier audit, conformity verification, procurement decision, or program-schedule forecast.

## Scope

The module composes the existing AeroCIE-029 supplier screen and AeroCIE-030 source adapters. It does not modify the scoring logic or connect to a third-party API.

- Reconcile local JSON and integrity-pinned CSV inputs to deterministic model reports.
- Independently recalculate record counts, assumption flags and report fingerprints.
- Keep individual SHA-256 digests for synthetic evidence, suppliers and components.
- Raise review questions for unreferenced evidence and supplier metadata.
- Link each lead-time or single-source flag to the exact fictional evidence identifier and fingerprint.
- Compare two validated synthetic snapshots for added, removed and modified record IDs.
- Produce a JSON review packet and a human-readable Markdown summary, with no raw evidence excerpts.
- Preserve external_release_authorized=false and require human review.

## Windows verification steps

From the aviation-ai-workflow directory:

    $env:PYTHONUTF8 = "1"
    $env:PYTHONIOENCODING = "utf-8"
    python -m unittest discover -s tests -p "test_aerocie_prime_reconciliation.py" -v

Generate a new set of reports:

    python -m src.aerocie.prime_reconciliation --adapter json --source sample-data/prime_scrm_synthetic.json --output-json build/prime-review-v1.json --output-md build/prime-review-v1.md

The CLI refuses to overwrite outputs. Use new paths for every additional run.

Compare a fictional revised JSON input against the existing fictional reference:

    python -m src.aerocie.prime_reconciliation --adapter json --source path/to/revised_synthetic.json --baseline-adapter json --baseline-source sample-data/prime_scrm_synthetic.json --output-json build/prime-diff-v1.json --output-md build/prime-diff-v1.md

CSV bundles can be used by setting the adapter to csv and supplying a manifest-pinned directory. See aerocie-030-portable-adapters.md.

## Output contract

- Schema: SRP-SCRM-REVIEW-PACKET-v1.
- Classification: PUBLIC_SYNTHETIC_ONLY, declared and not independently verified.
- Release authorized: false.
- Decision status: HUMAN_REVIEW_REQUIRED.
- Fingerprints: source_input_sha256, model_report_sha256 and packet_sha256. These are not electronic signatures or independently authenticated provenance.
- Source record ledger: source_record_sha256 for evidence, suppliers and components.
- Independent metric check: model_summary reconciles computed counts, single-source assumptions and flagged items against actual component records.
- Flag queue: open_review_items records component, supplier and evidence IDs, the evidence fingerprint, scenario delta, assumption flags and human disposition OPEN_NOT_REVIEWED.
- Data quality: data_quality_findings reports unreferenced metadata, without inferring compliance failures.
- Baseline: source_changes_since_baseline reports added, removed and modified record IDs.
- Review: reviewer_disposition is NOT_RECORDED. No credentialed review, signature verification or approval workflow exists.

## Required acceptance gates

1. Run the existing GitHub CI and the new dedicated regression tests against the exact PR head.
2. Independently run the CLI and tests on Windows before final review.
3. Verify rejection of tampered evidence, CUI or FCI classification, unrecognized references, altered model totals, invented schedule forecasts, and output overwrites.
4. Demonstrate identical input and model hashes through JSON and CSV adapters for equivalent fictional inputs.
5. Preserve the draft PR until architecture, security and data provenance limitations are reviewed.

## Limitations

These are self-declared synthetic records and SHA-256 integrity checks, not independently authenticated third-party data. No live manufacturer, supplier, ERP, MBSE, PLM, government, insurance or other authorized source is connected. No CUI, FCI, classified, export-controlled, personal, or customer data is permitted. The proof of concept does not establish MOSA conformance, CMMC Level 2 status, contract eligibility, actual supplier dependencies, true schedule criticality or program loss estimates.

The next independent milestones are real-source authorization and data-use mapping, explicit reviewer identity and signed dispositions, controlled retention, and program-specific security testing. Do not promote this research packet as a production customer deliverable.
