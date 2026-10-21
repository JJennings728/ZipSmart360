"""Offline AeroCIE-007 tests: SQLite handles closed; no network, credentials or customer data."""
from __future__ import annotations
from contextlib import closing
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from src.aerocie.fr_collector import initialize, ingest
from src.aerocie import reviewer_packet as rp


class ReviewerPacketTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.db = self.root / "federal_register.sqlite3"
        self.reviews = self.root / "receipts"
        self.doc = "2026-21290"
        self.row = {
            "document_number": self.doc, "title": "Synthetic Pratt rule",
            "type": "Rule", "publication_date": "2026-10-19", "effective_on": "2026-11-23",
            "action": "Final rule", "abstract": "Synthetic engine",
            "html_url": "https://www.federalregister.gov/documents/2026/10/19/2026-21290/test",
            "pdf_url": "https://www.govinfo.gov/content/pkg/FR-2026-10-19/pdf/2026-21290.pdf",
        }
        with closing(sqlite3.connect(self.db)) as conn:
            initialize(conn)
            ingest(conn, self.row, source="published")

    def record(self, **kwargs):
        common = dict(document_number=self.doc, reviewer="Test Person", reviewer_role="Aviation source reviewer",
                      notes="Checked the Federal Register and noted model restrictions.")
        common.update(kwargs)
        return rp.record_review(self.db, self.reviews, **common)

    def test_snapshot_hash_matches(self):
        item = rp.snapshot(self.db, self.doc)
        self.assertEqual(item["source"], "published")
        self.assertEqual(len(item["fingerprint"]), 64)

    def test_missing_document_rejected(self):
        with self.assertRaises(ValueError):
            rp.snapshot(self.db, "2026-99999")

    def test_path_traversal_rejected(self):
        with self.assertRaises(ValueError):
            self.record(document_number="../oops")

    def test_hold_record_not_verification(self):
        result = self.record()
        self.assertEqual(result["disposition"], "hold_for_review")
        state = rp.find_current_review(self.reviews, self.doc, rp.snapshot(self.db, self.doc)["fingerprint"])
        self.assertEqual(state["state"], "held_for_review")

    def test_cannot_mark_source_reviewed_without_all_checks(self):
        for flags in ({}, {"federal_register_checked": True, "faa_drs_checked": True},
                      {"federal_register_checked": True, "supersession_checked": True}):
            with self.assertRaises(ValueError):
                self.record(disposition="source_reviewed_research_only", **flags)

    def test_cannot_claim_review_without_notes(self):
        with self.assertRaises(ValueError):
            self.record(notes="ok")

    def test_fully_checked_receipt_research_only(self):
        self.record(disposition="source_reviewed_research_only", federal_register_checked=True,
                    faa_drs_checked=True, supersession_checked=True)
        state = rp.find_current_review(self.reviews, self.doc, rp.snapshot(self.db, self.doc)["fingerprint"])
        self.assertEqual(state["state"], "source_reviewed_research_only")
        self.assertNotIn("compliant", state["state"])

    def test_tampered_receipt_fails_closed(self):
        result = self.record(disposition="source_reviewed_research_only", federal_register_checked=True,
                             faa_drs_checked=True, supersession_checked=True)
        p = Path(result["receipt_path"])
        content = json.loads(p.read_text())
        content["reviewer"] = "Impostor"
        p.write_text(json.dumps(content))
        state = rp.find_current_review(self.reviews, self.doc, rp.snapshot(self.db, self.doc)["fingerprint"])
        self.assertEqual(state["state"], "integrity_problem_requires_review")

    def test_changed_snapshot_makes_review_stale(self):
        self.record(disposition="source_reviewed_research_only", federal_register_checked=True,
                    faa_drs_checked=True, supersession_checked=True)
        with closing(sqlite3.connect(self.db)) as conn:
            ingest(conn, {**self.row, "title": "Updated by collector"}, source="published")
        current = rp.find_current_review(self.reviews, self.doc, rp.snapshot(self.db, self.doc)["fingerprint"])
        self.assertEqual(current["state"], "stale_or_unreviewed")

    def test_unreviewed_packet_stays_internal(self):
        out = self.root / "packet.html"
        result = rp.create_packet(self.db, self.reviews, out=out, keyword="Pratt", as_of="2026-10-21")
        text = out.read_text()
        self.assertEqual(result["records"], 1)
        self.assertEqual(result["source_reviewed"], 0)
        self.assertIn("UNREVIEWED INTERNAL DRAFT", text)
        self.assertIn("NOT AUTOMATICALLY APPROVED", text)
        self.assertIn("@media print", text)

    def test_reviewed_packet_still_needs_release_approval(self):
        self.record(disposition="source_reviewed_research_only", federal_register_checked=True,
                    faa_drs_checked=True, supersession_checked=True)
        out = self.root / "packet.html"
        result = rp.create_packet(self.db, self.reviews, out=out, keyword="Pratt")
        text = out.read_text()
        self.assertEqual(result["source_reviewed"], 1)
        self.assertIn("SOURCE-REVIEWED INTERNAL DRAFT", text)
        self.assertIn("NOT AUTOMATICALLY APPROVED FOR CLIENT DISTRIBUTION", text)
        self.assertNotIn("COMPLIANT", text)

    def test_existing_db_is_unchanged(self):
        before = self.db.read_bytes()
        self.record()
        rp.create_packet(self.db, self.reviews, out=self.root/"packet.html")
        self.assertEqual(before, self.db.read_bytes())

    def test_html_escaped_and_host_approved(self):
        raw = {"document_number": self.doc, "title": "<script>alert(1)</script>",
               "source_url": "javascript:alert(1)", "publication_category": "rule",
               "review": {"state": "held_for_review", "reviewer": "<img src=x onerror=alert(1)>",
                          "reviewer_role": "Test", "notes": "<script>alert(2)</script>", "reviewed_at": "now"}}
        text = rp.render_packet([raw], as_of="2026-10-21")
        self.assertNotIn("<script>", text)
        self.assertNotIn("<img src=x", text)
        self.assertNotIn('href="javascript:', text)
        self.assertIn("&lt;script&gt;", text)

    def test_empty_packet_not_clearance(self):
        html = rp.render_packet([], as_of="2026-10-21")
        self.assertIn("does not indicate regulatory clearance", html)

    def test_bad_date_or_limit(self):
        with self.assertRaises(ValueError):
            rp.create_packet(self.db, self.reviews, out=self.root/"out.html", limit=1001)
        with self.assertRaises(ValueError):
            rp.render_packet([], as_of="2026-99-99")

    def test_second_review_does_not_replace_receipt(self):
        x = self.record()
        y = self.record(notes="This is a distinct additional research review performed after the first.")
        self.assertNotEqual(x["receipt_path"], y["receipt_path"])
        self.assertTrue(Path(x["receipt_path"]).exists())
        self.assertTrue(Path(y["receipt_path"]).exists())


if __name__ == "__main__":
    unittest.main()
