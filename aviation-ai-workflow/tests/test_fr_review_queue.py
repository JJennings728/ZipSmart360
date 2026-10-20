"""AeroCIE read-only queue tests. Standard library only."""
import argparse
from contextlib import closing
import datetime as dt
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from src.aerocie.fr_collector import ingest, initialize
from src.aerocie.review_queue import classify, latest_documents, write_csv


class TestReviewQueue(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / "federal_register.sqlite3"
        self.proposal = {"document_number":"2026-21298", "title":"Airworthiness Directives; Pratt & Whitney RTX Engines",
                         "type":"PRORULE", "action":"Notice of proposed rulemaking (NPRM).",
                         "publication_date":"2026-10-19", "effective_on":None,
                         "html_url":"https://www.federalregister.gov/documents/example"}
        self.final = {"document_number":"2026-21290", "title":"Airworthiness Directives; Pratt & Whitney Engines",
                      "type":"RULE", "action":"Final rule.", "publication_date":"2026-10-19",
                      "effective_on":"2026-11-23", "html_url":"https://www.federalregister.gov/documents/example2"}
        with closing(sqlite3.connect(self.db)) as c:
            initialize(c)
            ingest(c,self.proposal,source="published")
            ingest(c,self.final,source="published")

    def test_proposal_not_marked_effective(self):
        records = latest_documents(self.db,keyword="2026-21298",as_of="2026-10-20")
        self.assertEqual(records[0]["publication_category"],"proposed_rule")
        self.assertEqual(records[0]["triage_status"],"proposal_not_an_adopted_final_rule")
        self.assertFalse(records[0]["asset_applicability_verified"])

    def test_future_effective_date(self):
        records = latest_documents(self.db,keyword="2026-21290",as_of="2026-10-20")
        self.assertEqual(records[0]["triage_status"],"published_rule_future_reported_effective_date")
        self.assertEqual(records[0]["reported_effective_on"],"2026-11-23")

    def test_change_is_read_only(self):
        with closing(sqlite3.connect(self.db)) as c:
            first=c.execute('select count(*) from document_snapshots').fetchone()[0]
        latest_documents(self.db)
        with closing(sqlite3.connect(self.db)) as c:
            second=c.execute('select count(*) from document_snapshots').fetchone()[0]
        self.assertEqual(first,second)

    def test_filter_and_csv(self):
        recs=latest_documents(self.db,keyword="pratt",as_of="2026-10-20")
        self.assertEqual(len(recs),2)
        csv_data=write_csv(recs)
        self.assertIn("publication_category",csv_data)
        self.assertIn("2026-21290",csv_data)

    def test_unknown_is_review_not_compliant(self):
        rec=classify({"source":"published", "document_type":None},as_of="2026-10-20")
        self.assertEqual(rec["triage_status"],"unclassified_manual_review")
        self.assertTrue(rec["review_required"])

    def test_inspection_is_separate(self):
        rec=classify({"source":"public_inspection", "document_type":"PRORULE"},as_of="2026-10-20")
        self.assertEqual(rec["triage_status"],"public_inspection_not_published")

    def test_missing_database_has_clear_error(self):
        with self.assertRaises(FileNotFoundError):
            latest_documents(Path(self.tmp.name)/"nonexistent.sqlite3")


if __name__ == "__main__":
    unittest.main()
