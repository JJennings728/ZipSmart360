# AeroCIE-011 | Offline effective-date intelligence

**Research prototype only | NOT_DETERMINED | external_release_authorized=false**

The offline timeline reads locally pinned, **published Federal Register metadata**; it does not fetch new data, write to collector/graph SQLite databases, or determine the actual legal effective status or applicability of a rule.

## Outputs

- Publication date and *stated* effective date as separate fields (no fallback from one to the other).
- Calendar comparison against a user-provided as-of date, labeled **NOT_LEGAL_STATUS**.
- Collector snapshot version history with SHA-256 checks. Metadata changes **are not** automatically formal regulatory amendments.
- Previously reviewed, proposed CORRECTS graph candidates with **both source pins revalidated** by AeroCIE-010. Missing or stale pins require human review.
- Deterministic JSON event timeline and explicit limitations; no compliance approval, no customer release, no inference from shared dockets.

## Windows usage

From the existing aviation-ai-workflow project:

~~~powershell
py -m unittest tests.test_aerocie_effective_dates -v
py -m unittest discover -s tests -q

py -m src.aerocie.effective_dates --as-of 2026-10-28 --document-number 2026-19391 --document-number 2026-21995
~~~

Use --source-db and --graph-db to point at existing separate local databases. Omit --document-number to show the 25 most recently **locally observed** published records, capped at 100. Output goes to stdout and can be redirected to a local JSON report.

## Non-goals and review gate

No date is automatically declared legally operative. No amendment or supersession inference, cloud hosting, production dashboard, customer data, automatic AI interpretation or client-facing report. A valid SHA-256 is not authoritative authentication, and local metadata is not a live FAA DRS or official-publication recheck. Human review of current official texts, cited corrections, amendments, applicability and source recency remains mandatory. PR must stay draft until review and CI checks pass.
