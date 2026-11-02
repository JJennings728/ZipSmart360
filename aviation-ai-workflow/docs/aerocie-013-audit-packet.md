# AeroCIE-013 - Phase 17 Internal Evidence Review Packet

Unsigned research only. A new offline packet combines the Phase 16 subject candidate, both local publication metadata pins, chronology, graph-local corrections and existing self-attested source-review receipts. Output is an offline HTML page and JSON with a SHA-256 integrity checksum. The checksum is NOT a signature. The packet cannot certify FAA applicability, current legal operative status, completeness of amendments, compliance, asset risk or customer release.

All eight analyst-review checks start PENDING_HUMAN_REVIEW. Review disposition is HOLD_FOR_HUMAN_REVIEW. Human review complete remains false; compliance and applicability remain NOT_DETERMINED and client release remains unauthorized.

## Tests

From aviation-ai-workflow run:

~~~powershell
python -m pytest tests/test_aerocie_audit_packet.py -q
python -m pytest -q
~~~

## CLI

Run with three existing separate databases and a real locally assigned exposure candidate ID, directing output to two NEW paths:

~~~powershell
python -m src.aerocie.audit_packet --registry-db "EXPOSURE.sqlite3" --source-db "FEDERAL_REGISTER.sqlite3" --graph-db "GRAPH.sqlite3" --candidate-id 1 --as-of 2026-10-28 --out-json "NEW_PACKET.json" --out-html "NEW_PACKET.html"
~~~

Optional --reviews-dir selects preexisting human source-review receipts. Neither this module nor generation writes to the source, knowledge graph or candidate SQLite databases. Existing outputs are not overwritten. The packet does not generate reviewer attestations.

Before any external use, independent humans must check actual official texts, FAA DRS, amendments, dates and real subject facts, complete a documented applicability review, and conduct security/code review. Depend on draft PR #8, #10, #11, #12; no merges or deployments.
