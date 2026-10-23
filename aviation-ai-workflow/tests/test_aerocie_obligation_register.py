"""Offline tests for AeroCIE-008: no network and no compliance approval."""
from contextlib import closing
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
        self.assertEqual(len(result["source_fingerprint"]), 64)
        self.assertEqual(result["source_status"], "SOURCE_SNAPSHOT_CURRENT")

    def test_snapshot_change_fails_closed(self):
        self.add()
        with closing(sqlite3.connect(self.source_db)) as conn:
            ingest(conn, {**self.faa_row, "title": "Changed source metadata"}, source="published")
        result = reg.candidates(self.db, self.source_db)[0]
        self.assertEqual(result["source_status"], "SOURCE_CHANGED_REVIEW_REQUIRED")

    def test_unavailable_source_fails_closed(self):
        self.add()
        result = reg.candidates(self.db, self.source_db.parent / "missing.sqlite3")[0]
        self.assertEqual(result["source_status"], "SOURCE_UNAVAILABLE_REVIEW_REQUIRED")

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


if __name__ == "__main__":
    unittest.main()
