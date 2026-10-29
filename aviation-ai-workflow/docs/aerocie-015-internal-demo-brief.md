# AeroCIE-015 — Internal Synthetic Demo Brief

Standalone HTML for a synthetic AeroCIE-013 research packet and optional AeroCIE-014 journal.

- Reads the packet via existing checksum validation, and the optional journal via the existing audit-chain validation.
- Only synthetic research subjects (demo: IDs and Synthetic labels) are accepted.
- Renders publication cards, Federal Register links, proposed corrections, checks completed and unresolved issues.
- Excludes self-attested reviewer names, private notes and citation texts.
- Escapes all display values, restricts external links to Federal Register host, emits no scripts.
- Refuses to overwrite existing files or modify the source databases.
- No client release, FDA/FAA certification, legal applicability or current-authority claim. All unresolved human-review work remains unresolved.

From aviation-ai-workflow:

~~~powershell
python -m pytest tests/test_aerocie_demo_brief.py -q
python -m pytest -q
python -m src.aerocie.demo_brief --packet "EXISTING_PHASE17_PACKET.json" --journal "EXISTING_PHASE18_JOURNAL.sqlite3" --out-html "NEW_LOCAL_DEMO.html"
Start-Process "NEW_LOCAL_DEMO.html"
~~~

Draft PR stacked on AeroCIE-014 PR #14. No merge, deployment or customer data without further review.
