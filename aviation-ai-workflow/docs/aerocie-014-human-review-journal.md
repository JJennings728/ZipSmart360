# AeroCIE-014 - Phase 18 Self-Attested Research Review Journal

An offline, local **research step** journal for AeroCIE-013 unsigned evidence packets.

Each entry states which checklist item a human says they reviewed, their self-entered name and role, a detailed observation, an independently entered source citation (required for CHECKED_RESEARCH_ONLY), UTC timestamp, and an explicit typed attestation flag. FOLLOW_UP_REQUIRED may be used instead of claiming a check was complete. Each entry stores the hash of the previous entry and its own canonical SHA-256; SQLite transactions serialize writers and triggers block accidental UPDATE or DELETE of review events. Event-chain checks detect ordinary record modifications. This is **not cryptographically signed or independently identity authenticated** and does not prevent a privileged database administrator from replacing the entire history.

A journal is pinned to a specific JSON packet digest; changed/reissued packets need a separate journal. It never modifies original collector, graph, or exposure databases. A preexisting non-review SQLite file is rejected.

All status summaries remain HOLD_FOR_HUMAN_REVIEW, NOT_DETERMINED and external_release_authorized=false, **even if eight research steps are recorded**. It does not implement legal sign-off or release authorization.

From aviation-ai-workflow:

~~~powershell
python -m pytest tests/test_aerocie_review_journal.py -q
python -m pytest -q

# Inspect an unsigned packet without writing review data.
python -m src.aerocie.review_journal --packet "EXISTING_AEROCIE_013_PACKET.json" --journal "NEW_REVIEW_EVENTS.sqlite3" status

# After an actual human review of the relevant evidence, enter ONE attested step.
python -m src.aerocie.review_journal --packet "EXISTING_AEROCIE_013_PACKET.json" --journal "NEW_REVIEW_EVENTS.sqlite3" record-check --check-id source_text --status CHECKED_RESEARCH_ONLY --reviewer "YOUR NAME" --reviewer-role "Internal Research Reviewer" --notes "SPECIFIC STEPS PERSONALLY COMPLETED, WITH OUTSTANDING QUESTIONS" --citation "VERIFIED OFFICIAL SOURCE URL AND EXACT SECTION OR PAGE" --attest

# Record incomplete work rather than inventing a finding:
python -m src.aerocie.review_journal --packet "EXISTING_AEROCIE_013_PACKET.json" --journal "NEW_REVIEW_EVENTS.sqlite3" record-check --check-id later_changes --status FOLLOW_UP_REQUIRED --reviewer "YOUR NAME" --reviewer-role "Internal Research Reviewer" --notes "A manual search for later amendments has not yet been completed." --attest
~~~

Do not record a review you have not done. The --attest flag is a user-entered self-attestation, not digital or FAA signature. Do not store actual personal or customer records in the prototype.

Draft dependency chain: AeroCIE-009 PR #8 -> -010 PR #10 -> -011 PR #11 -> -012 PR #12 -> -013 PR #13 -> AeroCIE-014. Independent security, regulatory, and code review is required before any merge or customer release.
