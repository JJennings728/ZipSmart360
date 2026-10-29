# AeroCIE-012 | Research-only aviation exposure mapping

**State: PROPOSED_RESEARCH_ONLY | applicability: NOT_DETERMINED | external_release_authorized=false**

This is an offline evidence-association prototype. It links manually entered *synthetic internal research subjects* (FACILITY, AIRCRAFT, COMPONENT, OPERATION) to **published Federal Register metadata** already pinned in the collector and imported into the AeroCIE knowledge graph.

It does **not** determine FAA applicability, legal effect, operational exposure, insured loss, compliance or availability for customer delivery. A matching published source is only a candidate for human review.

## Evidence controls

- Keep the candidate registry in a **third SQLite database**, separate from the Federal Register collector and evidence graph.
- A subject has a stable local ID and type; renaming or retyping an existing ID is rejected.
- Candidate insertion requires a current, hash-verified locally published metadata snapshot, existing typed publication graph node, fingerprint-matched graph document, and exact excerpt contained in that graph document.
- The manually supplied source locator and substantive research rationale are preserved, not treated as official findings.
- At export, collector and graph pins are rechecked; stale, removed or altered evidence is flagged.
- All locally recorded CORRECTS edges involving a linked publication are surfaced with their status. A missing edge does not prove no amendments or corrections exist.
- No cloud network access, LLM auto-classification, customer data, certified applicability engine, legal status determination, deployment, or automatic release.
- All output contains NOT_DETERMINED and external_release_authorized=false.

## Testing

From the aviation-ai-workflow directory, run:

~~~powershell
py -m unittest tests.test_aerocie_exposure_map -v
py -m pytest tests/test_aerocie_exposure_map.py -q
py -m pytest -q
~~~

## Example with synthetic subjects

First obtain an existing local pinned published source graph (including a PUBLICATION node). Never point --db at either original evidence database. Use dummy subjects, not customer/insured records.

~~~powershell
py -m src.aerocie.exposure_map --db build/aerocie/demo-exposure.sqlite3 --source-db build/aerocie/federal_register.sqlite3 --graph-db build/aerocie/knowledge_graph.sqlite3 add-subject --subject-id demo:facility:1 --type FACILITY --label "Synthetic facility"
~~~

Then invoke propose with the publication number, a literal excerpt from its pinned metadata, and a human-written rationale. Finally, use export to inspect provenance and review status.

## Human acceptance gate

Review actual publication text, current source authority, FAA DRS and later corrections, rule applicability, and the underlying operational facts manually. Treat all candidates as internal research only. Complete an independent code/security review before merging. The dependency chain is AeroCIE-009 PR #8, AeroCIE-010 PR #10, AeroCIE-011 PR #11, then this feature. No merges or deployments are part of this PR.
