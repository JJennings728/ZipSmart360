"""AeroCIE-003: stdlib-only tests, no network; Windows-safe SQLite cleanup."""
from contextlib import closing
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.aerocie.fr_collector import initialize, ingest
from src.aerocie.asset_screen import (
    bounded_pattern, latest_snapshots, screen_documents, safe_csv_value, validate_model, write_csv,
)


class AssetScreenTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = Path(self.temp.name) / "federal_register.sqlite3"
        self.engine_rule = {
            "document_number": "2024-06419",
            "title": "Airworthiness Directives; International Aero Engines Engines",
            "type": "RULE",
            "action": "Final rule.",
            "abstract": "Certain PW1100G-JM engines with selected component histories.",
            "publication_date": "2024-03-27",
            "effective_on": "2024-04-11",
            "pdf_url": "https://www.govinfo.gov/content/pkg/example.pdf",
        }
        self.brand_proposal = {
            "document_number": "2026-21298",
            "title": "Airworthiness Directives; Pratt & Whitney Engines",
            "type": "PRORULE",
            "action": "Notice of proposed rulemaking",
            "abstract": "This proposal concerns other PW4000 family engines.",
            "publication_date": "2026-10-19",
            "effective_on": None,
        }
        self.other_rule = {
            "document_number": "2026-21290",
            "title": "Airworthiness Directives; Airbus SAS Airplanes",
            "type": "RULE",
            "abstract": "For models A320-200 and A321-200.",
            "publication_date": "2026-10-19",
            "effective_on": "2026-11-23",
        }
        with closing(sqlite3.connect(self.db)) as conn:
            initialize(conn)
            for entry in (self.engine_rule, self.brand_proposal, self.other_rule):
                ingest(conn, entry, source="published")

    def test_exact_model_reference_is_not_a_compliance_result(self):
        docs, trunc = latest_snapshots(self.db)
        out = screen_documents(docs, model="PW1100G", manufacturer="Pratt & Whitney", as_of="2026-10-20")
        self.assertEqual(out["model_mention_count"], 1)
        self.assertEqual(out["manufacturer_context_count"], 1)
        self.assertEqual(out["model_mentions"][0]["document_number"], "2024-06419")
        self.assertEqual(out["model_mentions"][0]["evidence_field"], "abstract")
        self.assertFalse(out["model_mentions"][0]["asset_applicability_verified"])
        self.assertFalse(trunc)

    def test_manufacturer_only_is_separate_and_proposal_unadopted(self):
        docs, _ = latest_snapshots(self.db)
        out = screen_documents(docs, model="PW1100G", manufacturer="Pratt & Whitney", as_of="2026-10-20")
        lead = out["manufacturer_context_only"][0]
        self.assertEqual(lead["screening_result"], "manufacturer_mention_only_not_model_match")
        self.assertEqual(lead["publication_category"], "proposed_rule")
        self.assertEqual(lead["triage_status"], "proposal_not_an_adopted_final_rule")

    def test_false_positive_similar_model_is_excluded(self):
        self.assertIsNotNone(bounded_pattern("PW1100G").search("PW1100G-JM"))
        self.assertIsNone(bounded_pattern("PW1100G").search("PW1100G2"))
        self.assertIsNone(bounded_pattern("PW1100G").search("XPW1100G"))

    def test_no_model_mention_is_not_clearance(self):
        docs, _ = latest_snapshots(self.db)
        out = screen_documents(docs, model="LEAP-1A", as_of="2026-10-20")
        self.assertEqual(out["model_mention_count"], 0)
        self.assertFalse(out["asset_applicability_verified"])
        self.assertIn("NOT proof", out["limitations"])

    def test_reads_latest_snapshot_and_does_not_modify_db(self):
        with closing(sqlite3.connect(self.db)) as conn:
            before = conn.execute("select count(*) from document_snapshots").fetchone()[0]
            ingest(conn, {**self.engine_rule, "abstract": "Updated wording mentions PW1100G explicitly"}, source="published")
        docs, _ = latest_snapshots(self.db)
        out = screen_documents(docs, model="PW1100G")
        self.assertEqual(out["model_mention_count"], 1)
        with closing(sqlite3.connect(self.db)) as conn:
            after = conn.execute("select count(*) from document_snapshots").fetchone()[0]
        self.assertEqual(after, before + 1)

    def test_scan_truncation_is_reported(self):
        docs, trunc = latest_snapshots(self.db, scan_limit=2)
        self.assertEqual(len(docs), 2)
        self.assertTrue(trunc)

    def test_model_validation_and_asof(self):
        with self.assertRaises(ValueError):
            validate_model("P")
        with self.assertRaises(ValueError):
            validate_model(".*")
        docs, _ = latest_snapshots(self.db)
        with self.assertRaises(ValueError):
            screen_documents(docs, model="PW1100G", as_of="2026-99-99")

    def test_csv_contains_source_fields(self):
        docs, _ = latest_snapshots(self.db)
        out = screen_documents(docs, model="PW1100G", manufacturer="Pratt & Whitney")
        data = write_csv(out)
        self.assertIn("manufacturer_mention_only_not_model_match", data)
        self.assertIn("https://www.govinfo.gov/content/pkg/example.pdf", data)

    def test_spreadsheet_formula_escape(self):
        self.assertEqual(safe_csv_value("=1+1"), "'=1+1")
        self.assertEqual(safe_csv_value("Safe Title"), "Safe Title")

    def test_missing_database(self):
        with self.assertRaises(FileNotFoundError):
            latest_snapshots(Path(self.temp.name) / "missing.sqlite3")


if __name__ == "__main__":
    unittest.main()
