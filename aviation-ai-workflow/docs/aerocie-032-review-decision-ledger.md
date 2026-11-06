# AeroCIE-032 | Synthetic Reviewer-Decision Ledger

**Stage:** Internal research prototype. This is not an authenticated reviewer identity service, a legally binding electronic signature, an immutable ledger, an external audit, a production records system, or a compliance authorization.

## Purpose

Keep the human review record separate from supplier-risk scoring. The existing AeroCIE-031 packet contains synthetic evidence-linked findings; this module creates a local SQLite journal whose events are bound to that packet's SHA-256 and to an explicit component in its review queue.

### Included controls

- Only the existing SRP-SCRM-REVIEW-PACKET-v1 synthetic review packet is accepted. An invalid packet digest, a release-authorized packet, an unreviewed status mismatch, or sensitive-data classification fails closed.
- One new local SQLite journal per input packet; file overwrite is refused.
- Valid dispositions are RESEARCH_ACKNOWLEDGED, MORE_EVIDENCE_REQUIRED and REJECT_RESEARCH_FINDING. **There is no release approval operation.**
- Events include sequence number, self-declared reviewer ID, key ID, UTC timestamp, evidence fingerprint, disposition, reason, previous event SHA-256 and packet SHA-256.
- HMAC-SHA-256 using a locally supplied shared test key authenticates an event to a key holder, **not to a particular human**.
- An event digest links the events; normal SQLite UPDATE/DELETE operations are blocked by triggers. A sufficiently privileged person can bypass database triggers and recreate a database.
- Every verification reads and checks the chain; a previously retained head digest can detect deletion of the last event. Without an external retained anchor, deletion or full replacement of a journal cannot be conclusively detected.
- The verifier returns a status with external_release_authorized=false regardless of disposition.

## Run with synthetic records only

Run from the aviation-ai-workflow directory on Python 3.11+.

1. Generate a fresh synthetic source-review packet (AeroCIE-031):

    python -m src.aerocie.prime_reconciliation --adapter json --source sample-data/prime_scrm_synthetic.json --output-json build/demo-packet.json

2. Initialize a fresh demonstration journal:

    python -m src.aerocie.review_decision_ledger init --db build/demo-journal.sqlite3 --packet build/demo-packet.json

3. Use a new **test-only secret** generated locally, stored only in the current PowerShell session. Never commit or share the secret. Example PowerShell:

    $env:SRP_REVIEW_HMAC_KEY_HEX = py -3.14 -c "import secrets; print(secrets.token_hex(32))"

4. Record a purely fictional research review decision:

    python -m src.aerocie.review_decision_ledger record --db build/demo-journal.sqlite3 --component C001 --reviewer REVIEWER_01 --decision MORE_EVIDENCE_REQUIRED --reason "Fictional lead time requires independent corroboration." --key-id TESTKEY_01

5. Verify the journal, optionally supplying an externally retained head SHA-256 value from the previous record operation:

    python -m src.aerocie.review_decision_ledger verify --db build/demo-journal.sqlite3

    python -m src.aerocie.review_decision_ledger verify --db build/demo-journal.sqlite3 --expected-head YOUR_RETAINED_SHA256

6. Clear the test key from PowerShell when no longer needed:

    Remove-Item Env:SRP_REVIEW_HMAC_KEY_HEX

Run tests without configuring any real key:

    python -m unittest discover -s tests -p "test_aerocie_review_decision_ledger.py" -v

Use fresh filenames for every attempt; outputs are not overwritten. Do not use sensitive, customer, manufacturer-proprietary, export-controlled, FCI, CUI or classified records. Never paste actual keys into GitHub, ChatGPT, web forms or code comments.

## What the HMAC does and does not prove

A correctly verified HMAC shows the event data matches a secret available to the signer and verifier. It does not establish the reviewer's actual identity, their organizational authority, the identity of an individual who handled a shared key, legal nonrepudiation, trusted time, or independent data provenance.

These requirements remain unimplemented and must be explicitly scoped before any real customer use: independent identity and access controls, separate signers/verifiers, secret storage and rotation, externally anchored immutable retention, authenticated source systems, reviewer training, customer permissions, export controls, encryption at rest, backed-up records, contract-specific NIST/CMMC requirements, security testing, and organizational change approval.

## Release boundary and next milestone

A research acknowledgement is not authority to change a model, issue a supplier finding, certify regulatory compliance, bind insurance, purchase parts or release information. All outputs remain internal synthetic demonstration material.

Next: create a **controlled report-export gate** that refuses export of real/non-synthetic data, checks the source packet hash against the decision journal, and generates a clearly watermarked internal demonstration package. That workflow is distinct from release approval and must not claim CMMC certification or program conformity.
