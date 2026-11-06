# AeroCIE-033 | Controlled Internal Demonstration Export

**Status:** Offline, synthetic-only research demonstration. Not a customer-delivery mechanism, not a real supplier audit, not a CMMC system, and not authority to release records.

## Purpose

This module consumes the synthetic source-linked AeroCIE-031 packet and local AeroCIE-032 research-review journal to create a clearly watermarked internal ZIP demonstration. The module does not connect to external systems or alter analytical scores.

**Export gates:** Before writing a file, the tool must validate the journal HMAC with the locally supplied key, match a separately retained head SHA-256, verify the original synthetic review packet, confirm every flagged component's **latest** decision is RESEARCH_ACKNOWLEDGED, and confirm the output does not already exist. An incomplete review or MORE_EVIDENCE_REQUIRED disposition blocks the export.

Research acknowledgement is **not external release approval**. Export still produces only an internal synthetic package; the output explicitly includes release_authorized=false.

## Example test-only Windows workflow

Use the existing fictional fixture under aviation-ai-workflow.

    $env:PYTHONUTF8 = "1"
    python -m src.aerocie.prime_reconciliation --adapter json --source sample-data/prime_scrm_synthetic.json --output-json build/prime-packet-demo.json

    python -m src.aerocie.review_decision_ledger init --db build/prime-journal-demo.sqlite3 --packet build/prime-packet-demo.json

Generate a new **demo-only** local HMAC key if one is not already being used for this specific journal. Never share, upload, or commit the key.

    $env:SRP_REVIEW_HMAC_KEY_HEX = py -3.14 -c "import secrets; print(secrets.token_hex(32))"

A hypothetical research reviewer must acknowledge **both** flagged fictional components C001 and C003 (the exact reviewer role/identity is not authenticated). Run these commands in the same environment that contains the demo key:

    python -m src.aerocie.review_decision_ledger record --db build/prime-journal-demo.sqlite3 --component C001 --reviewer SYNTHETIC_REVIEWER --decision RESEARCH_ACKNOWLEDGED --reason "Fictional source reviewed for internal scenario demonstration only." --key-id SYNTHETIC_TESTKEY

    python -m src.aerocie.review_decision_ledger record --db build/prime-journal-demo.sqlite3 --component C003 --reviewer SYNTHETIC_REVIEWER --decision RESEARCH_ACKNOWLEDGED --reason "Fictional second source reviewed for demonstration only." --key-id SYNTHETIC_TESTKEY

Record the **journal_head_sha256** returned by the **last** operation separately from the SQLite file. It must be supplied for export, and must not be guessed or copied from untrusted journal content.

    python -m src.aerocie.prime_internal_export --db build/prime-journal-demo.sqlite3 --out build/prime-internal-demo.zip --expected-head PASTE_RETAINED_HEAD_SHA256

Clear the demo-only environment key afterward:

    Remove-Item Env:SRP_REVIEW_HMAC_KEY_HEX

## Contents of successful internal ZIP

- READ_ME_FIRST.txt — plain-language no-customer-release watermark and synthetic provenance limitations.
- internal_research_report.json — verified synthetic summary, component research dispositions, evidence ID fingerprints and release_authorized=false; **no raw source excerpts**.
- manifest.json — SHA-256 fingerprints for the fixed ZIP member names; not a cryptographic signature of origin.

The ZIP entries have fixed names and metadata to enable reproducible file bytes for an unchanged journal. All output files are newly created; existing files are not overwritten. The HMAC secret is not stored in the database or packaged.

## Verification

Run on Python 3.11+ from aviation-ai-workflow:

    python -m unittest discover -s tests -p "test_aerocie_prime_internal_export.py" -v
    python -m unittest discover -s tests -p "test_aerocie_review_decision_ledger.py" -v

CI on exact commit and independent Windows testing remain required before promoting the research prototype. A package is not proof that a human reviewer is authenticated: reviewer_id is self-declared, shared HMAC keys do not provide nonrepudiation, and the retained head digest must be stored in an independently trusted location to help detect truncation.

## No-go boundaries

No CUI, FCI, actual supplier records, classified material, export-controlled data, customer records, insurance decisions, governmental certifications, legal applicability conclusions, or operational manufacturing decisions. No production deployment, client delivery, real security accreditation, MOSA compliance claim, government endorsement, or CMMC certification. All output is explicitly **internal synthetic research** only.

## Next acceptance gates

1. Windows regression on Python 3.14 with warnings treated as errors.
2. Human security review of the trust boundary, key storage, disposal and independently retained head.
3. Add separate authorized-data ingestion, authenticated identity, role-based approval, and controlled customer release under a new and appropriately reviewed deployment policy. None are implied by the demo.
