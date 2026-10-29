# AeroCIE-010 | Research-only correction lineage

Prototype implementation from verified source metadata, extending AeroCIE-009.

## Typed `CORRECTS` candidate

- Graph direction: correcting publication **CORRECTS** earlier publication.
- Both graph nodes must be `PUBLICATION` and use `frdoc:<document-number>` identifiers.
- Both documents must be individually pinned **published Federal Register metadata**; the evidence document must be the correction.
- Correction action/title, explicit original citation/date, shared docket, and chronology must agree. The exact evidence excerpt must identify the original and contain correction language.
- Source snapshot SHA-256 and most recent **local** metadata SHA-256 must match the pinned records.
- This protects against unsupported candidate relations but **does not certify legal effect, authoritative text, live freshness, final status, or FAA applicability**.
- All relationships remain `PROPOSED_RESEARCH_ONLY` and all exports retain `NOT_DETERMINED` and `external_release_authorized=false`.
- The production database schema has not changed; only the predicate vocabulary and a guarded validation branch have been added.

## Scope / acceptance

- The patch does not merge or deploy anything and does not modify existing collector databases.
- Unit tests use synthetic, locally generated Federal Register metadata; no API requests or customer data.
- The real-record demo uses a separate SQLite backup of the Ottawa pilot and is provisional pending human review of source PDFs and later amendments.
- A source change, incomplete text extraction, or missing human review prevents claiming the correction is legally verified.
- Re-run all existing tests and GitHub CI on any future PR before considering merger.
