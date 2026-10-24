"""Offline tests for AeroCIE-008: no network and no compliance approval."""
from contextlib import closing, redirect_stdout
import hashlib
import io
import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.aerocie.fr_collector import initialize as init_collector, ingest
from src.aerocie import obligation_register as reg


class ObligationRegisterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.source_db = root / "source.sqlite3"
        self.db = root / "candidates.sqlite3"
        self.document = "2026-21290"
        self.faa_row = {
            "document_number": self.document, "title": "Synthetic research record",
            "type": "Rule", "publication_date": "2026-10-19",
            "html_url": "https://www.federalregister.gov/documents/2026/10/19/2026-21290/synthetic",
        }
        with closing(sqlite3.connect(self.source_db)) as conn:
            init_collector(conn)
            ingest(conn, self.faa_row, source="published")

    def add(self, **updates):
        args = dict(document_number=self.document,
                    research_question="Does this source warrant qualified review?",
                    actor="Synthetic Reviewer", owner="Research Desk")
        args.update(updates)
        return reg.add_candidate(self.db, self.source_db, **args)

    def test_init_creates_local_db(self):
        reg.initialize(self.db)
        self.assertTrue(self.db.is_file())

    def test_new_candidate_never_compliance_approval(self):
        row = self.add()
        self.assertEqual(row["compliance_status"], "NOT_DETERMINED")
        result = reg.candidates(self.db, self.source_db)[0]
        self.assertFalse(result["external_release_authorized"])
        self.assertEqual(result["status"], "RESEARCH_CANDIDATE")

    def test_candidate_has_source_fingerprint(self):
        self.add()
        result = reg.candidates(self.db, self.source_db)[0]
        with sqlite3.connect(self.source_db) as conn:
            payload, digest = conn.execute(
                "SELECT payload_json, fingerprint FROM document_snapshots").fetchone()
        self.assertEqual(result["source_fingerprint"], digest)
        self.assertEqual(digest, hashlib.sha256(payload.encode("utf-8")).hexdigest())
        self.assertEqual(result["source_status"], "MATCHES_LATEST_LOCAL_METADATA_SNAPSHOT")

    def test_snapshot_change_fails_closed(self):
        self.add()
        with closing(sqlite3.connect(self.source_db)) as conn:
            ingest(conn, {**self.faa_row, "title": "Changed source metadata"}, source="published")
        result = reg.candidates(self.db, self.source_db)[0]
        self.assertEqual(result["source_status"], "SOURCE_CHANGED_REVIEW_REQUIRED")

    def test_unavailable_source_fails_closed(self):
        self.add()
        result = reg.candidates(self.db, self.source_db.parent / "missing.sqlite3")[0]
        self.assertEqual(result["source_status"], "PINNED_SOURCE_UNAVAILABLE_OR_INVALID_REVIEW_REQUIRED")

    def test_audit_events_recorded(self):
        row = self.add()
        reg.change_research_status(self.db, candidate_id=row["id"],
            state="RESEARCH_HOLD", actor="Test", notes="Source needs qualified review")
        audit = reg.events(self.db, row["id"])
        self.assertEqual(len(audit), 2)
        self.assertIn("RESEARCH_HOLD", audit[-1]["event"])

    def test_cannot_authorize_compliance(self):
        row = self.add()
        for state in ("COMPLIANT", "APPROVED", "SOURCE_REVIEWED"):
            with self.assertRaises(ValueError):
                reg.change_research_status(self.db, candidate_id=row["id"],
                    state=state, actor="Test", notes="Not allowed")
        self.assertEqual(len(reg.events(self.db, row["id"])), 1)

    def test_invalid_source_and_question_rejected(self):
        with self.assertRaises(ValueError):
            self.add(document_number="../escape")
        with self.assertRaises(ValueError):
            self.add(research_question=" ")

    def test_bad_internal_date_rejected(self):
        with self.assertRaises(ValueError):
            self.add(internal_review_by="yesterday")

    def test_missing_candidate_rejected(self):
        with self.assertRaises(ValueError):
            reg.change_research_status(self.db, candidate_id="missing",
                state="RESEARCH_HOLD", actor="Test", notes="Test")
        self.assertFalse(reg.candidates(self.db))

    def test_source_snapshot_db_not_modified(self):
        before = self.source_db.read_bytes()
        self.add()
        self.assertEqual(before, self.source_db.read_bytes())


    def test_same_path_and_file_aliases_rejected_without_source_write(self):
        aliases = [self.source_db, self.source_db.parent / "." / self.source_db.name]
        for kind in ("symlink", "hardlink"):
            alias = self.source_db.parent / (kind + ".sqlite3")
            try:
                if kind == "symlink":
                    alias.symlink_to(self.source_db)
                else:
                    os.link(self.source_db, alias)
            except OSError:
                continue  # Some Windows accounts cannot create links.
            aliases.append(alias)
        before = self.source_db.read_bytes()
        for alias in aliases:
            with self.subTest(alias=alias):
                with self.assertRaises(ValueError):
                    reg.add_candidate(alias, self.source_db, document_number=self.document,
                                      research_question="Test", actor="Test")
                self.assertEqual(before, self.source_db.read_bytes())

    def test_init_and_status_reject_collector_database(self):
        before = self.source_db.read_bytes()
        with self.assertRaises(ValueError):
            reg.initialize(self.source_db)
        with self.assertRaises(ValueError):
            reg.change_research_status(self.source_db, candidate_id="missing",
                                      state="RESEARCH_HOLD", actor="Test", notes="Test")
        self.assertEqual(before, self.source_db.read_bytes())

    def test_deleted_original_pin_is_not_just_a_changed_source(self):
        self.add()
        original = reg.candidates(self.db)[0]["source_fingerprint"]
        with sqlite3.connect(self.source_db) as conn:
            ingest(conn, {**self.faa_row, "title": "New revision"}, source="published")
            conn.execute("DELETE FROM document_snapshots WHERE fingerprint=?", (original,))
        row = reg.candidates(self.db, self.source_db)[0]
        self.assertEqual(row["source_fingerprint"], original)
        self.assertEqual(row["source_status"],
                         "PINNED_SOURCE_UNAVAILABLE_OR_INVALID_REVIEW_REQUIRED")

    def test_corrupt_original_pin_is_flagged_even_with_valid_latest(self):
        self.add()
        original = reg.candidates(self.db)[0]["source_fingerprint"]
        with sqlite3.connect(self.source_db) as conn:
            ingest(conn, {**self.faa_row, "title": "New revision"}, source="published")
            conn.execute("UPDATE document_snapshots SET payload_json='{}' WHERE fingerprint=?",
                         (original,))
        row = reg.candidates(self.db, self.source_db)[0]
        self.assertEqual(row["source_status"],
                         "PINNED_SOURCE_UNAVAILABLE_OR_INVALID_REVIEW_REQUIRED")
        self.assertEqual(row["source_fingerprint"], original)

    def test_changed_source_preserves_original_pin(self):
        self.add()
        original = reg.candidates(self.db)[0]["source_fingerprint"]
        with sqlite3.connect(self.source_db) as conn:
            ingest(conn, {**self.faa_row, "title": "New revision"}, source="published")
        row = reg.candidates(self.db, self.source_db)[0]
        self.assertEqual(row["source_fingerprint"], original)
        self.assertEqual(row["source_status"], "SOURCE_CHANGED_REVIEW_REQUIRED")
        self.assertFalse(row["external_release_authorized"])

    def test_malformed_latest_payload_fails_closed(self):
        self.add()
        for payload in ('[]', 'null', '42', '"text"', '{',
                        '{"document_number": [], "source": "published"}'):
            with self.subTest(payload=payload):
                with sqlite3.connect(self.source_db) as conn:
                    conn.execute("INSERT INTO document_snapshots "
                                 "(source,document_number,fingerprint,fetched_at,payload_json) "
                                 "VALUES ('published',?,?,?,?)",
                                 (self.document, hashlib.sha256(payload.encode()).hexdigest(),
                                  "2026-10-24T00:00:00Z", payload))
                row = reg.candidates(self.db, self.source_db)[0]
                self.assertEqual(row["source_status"], "SOURCE_UNAVAILABLE_REVIEW_REQUIRED")
                self.assertFalse(row["external_release_authorized"])
                with self.assertRaises(ValueError):
                    self.add()

    def test_public_inspection_only_cannot_create_candidate(self):
        with sqlite3.connect(self.source_db) as conn:
            conn.execute("DELETE FROM document_snapshots")
            ingest(conn, self.faa_row, source="public_inspection")
        with self.assertRaises(ValueError):
            self.add()
        self.assertFalse(self.db.exists())

    def test_all_research_states_keep_output_markers(self):
        created = self.add()
        self.assertFalse(created["external_release_authorized"])
        for state in reg.STATES[1:]:
            result = reg.change_research_status(self.db, candidate_id=created["id"],
                                               state=state, actor="Test", notes="Test")
            self.assertEqual(result["compliance_status"], "NOT_DETERMINED")
            self.assertFalse(result["external_release_authorized"])

    def test_every_successful_cli_command_has_safe_envelope(self):
        def call(*args):
            output = io.StringIO()
            with redirect_stdout(output):
                code = reg.main(["--db", str(self.db), "--source-db", str(self.source_db), *args])
            self.assertEqual(code, 0)
            value = json.loads(output.getvalue())
            self.assertEqual(value["compliance_status"], "NOT_DETERMINED")
            self.assertIs(value["external_release_authorized"], False)
            return value["result"]
        call("init")
        self.assertEqual(call("list"), [])
        self.assertEqual(call("history", "--id", "missing"), [])
        created = call("add-from-faa", "--document-number", self.document,
                       "--question", "Test", "--actor", "Test")
        for state in reg.STATES[1:]:
            call("status", "--id", created["id"], "--state", state,
                 "--actor", "Test", "--notes", "Test")
        self.assertEqual(len(call("list")), 1)
        self.assertEqual(len(call("history", "--id", created["id"])), 4)


if __name__ == "__main__":
    unittest.main()
