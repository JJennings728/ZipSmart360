# AeroCIE-009 | Source-linked knowledge graph

**Status:** Local prototype. **NOT_DETERMINED | external_release_authorized=false**. No regulatory applicability determinations, legal advice, client release, hosted dashboard, customer records or automatic AI extraction.

This adds an offline evidence graph to the existing `aviation-ai-workflow` project. It does not replace the AeroCIE-007 human source-review packet, AeroCIE-008 candidate register, or original Federal Register collector. Each graph relationship is a **manually proposed research association** backed by an exact excerpt from a pinned source. SHA-256 detects some accidental changes, but is not cryptographic authentication of a publication or tamper-proof audit logging.

## Data model

- **Document:** immutable local text or a byte-matched published Federal Register *metadata* snapshot, including title, public HTTPS URL, content SHA-256, timestamp and source category.
- **Node:** typed `ORGANIZATION`, `AIRCRAFT`, `COMPONENT`, `PUBLICATION`, `EVENT`, `REGULATION`, `TOPIC`, `FACILITY` or `OTHER` entity, with local ID and research label.
- **Edge:** `MENTIONS`, `REFERENCES`, `ASSOCIATED_WITH`, or `RESEARCH_RELATED_TO`, plus source document ID, the original document SHA-256, exact evidence excerpt, researcher-provided locator, author and time. Every edge remains `PROPOSED_RESEARCH_ONLY`.
- **Evidence audit:** verify stored evidence hash, quote presence, and, for Federal Register snapshots, existence of the original pinned metadata and comparison to the latest *local* metadata. A local metadata match is **not** live freshness, full-text governing authority, FAA DRS cross-check or applicability.

## Getting started on Windows PowerShell

From the existing `aviation-ai-workflow` folder, Python 3.11+ and no added packages:

```powershell
py -m unittest tests.test_aerocie_knowledge_graph -v
py -m src.aerocie.knowledge_graph init

# First source is explicitly SYNTHETIC. The URL is a non-resolving example.
py -m src.aerocie.knowledge_graph import-file --id demo:memo:1 --title "Synthetic research memo" --url "https://example.invalid/srp-synthetic" --file sample-data/aerocie-009-synthetic-note.txt
py -m src.aerocie.knowledge_graph add-node --id demo:aircraft --type AIRCRAFT --label "Demonstration aircraft (synthetic)"
py -m src.aerocie.knowledge_graph add-node --id demo:engine --type COMPONENT --label "Demonstration engine (synthetic)"
py -m src.aerocie.knowledge_graph add-link --from-id demo:aircraft --to-id demo:engine --predicate MENTIONS --doc-id demo:memo:1 --quote "a demonstration aircraft and a demonstration engine" --locator "Synthetic note | line 2" --actor "SRP internal research"
py -m src.aerocie.knowledge_graph stats
py -m src.aerocie.knowledge_graph neighbors --node demo:aircraft
py -m src.aerocie.knowledge_graph render-html
Start-Process build/aerocie/reports/knowledge-graph.html
```

### Link a real locally collected Federal Register record

The following demonstrates data flow; confirm the document actually exists as a published record before using it. A `document-number` is not itself an evaluated regulatory obligation.

```powershell
# Example only: use a real, verified number relevant to SRP's current collection.
py -m src.aerocie.fr_collector --mode document --document-number YOUR-VALID-NUMBER
py -m src.aerocie.knowledge_graph import-fr --document-number YOUR-VALID-NUMBER
```

The graph imports and pins collector **metadata**, never labels the metadata as authoritative statutory or regulatory text. Use `import-file` with a local text excerpt obtained under permissible rights when a specific passage is needed; preserve publication edition, citation, page or section locator, official URL, and date in your workflow. The quote must occur *exactly* in the pinned bytes. Do not enter private records, credentials, controlled technical data or unapproved proprietary content. Do not publish the local SQLite database.

## Human acceptance checklist

1. Source URLs and entity disambiguation are manually checked, including edition, corrections and effective/supersession status.
2. Confirm edge interpretation against the cited text. Being named together does **not** necessarily establish an operational, corporate or legal relationship.
3. For FAA questions, check governing legal text and FAA DRS independently. Document reviewer findings using approved existing research workflow.
4. Inspect SHA pin/integrity flags. Re-import genuinely changed documents using **a new versioned ID**, not by overwriting an earlier source.
5. Verify local/CI tests and qualified human review before merging this proposed implementation.
6. No public claims of verified regulatory coverage, 8,893 nodes, 9,000 indexed documents, automated reasoning, enterprise security or production readiness.

## Security and performance limitations

- Local single-user SQLite with no authentication, encryption at rest, immutable event vault, concurrency controls or privilege isolation. Run only in a trusted local environment. `build/` remains gitignored.
- The source URL is a traceability pointer, not proof the remote website currently serves the same content. There is no network access from the graph module.
- Local text is limited to 2 MB per import; SQL queries and SVG drawing are intentionally basic. The offline display is suitable for small research maps, **not** thousands of overlapping nodes.
- No claims of legally defensible evidentiary chain of custody. For formal matters preserve certified copies, acquisition logs, verifiable timestamps and reviewer sign-offs under a separately approved policy.
- `render-html` embeds research text in an offline HTML file: treat the output as sensitive internal research and **never** post it online without an authorized review.