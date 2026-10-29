"""AeroCIE-015 internal demo safety tests, synthetic fixtures only."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from src.aerocie import audit_packet, demo_brief, review_journal


class DemoBriefTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.packet = self.root / "packet.json"
        self.journal = self.root / "journal.sqlite3"
        self.out = self.root / "demo.html"
        self.data = {
            "packet_schema": "AEROCIE-013-UNSIGNED-RESEARCH-DRAFT-v1",
            "research_candidate": {
                "subject_id": "demo:facility:ottawa",
                "subject_label": "Synthetic Ottawa aviation facility",
                "rationale": "Local evidence candidate",
            },
            "published_metadata_documents": [{
                "document_number": "2026-21995",
                "title": "FAA Correction",
                "publication_date": "2026-10-28",
                "stated_effective_on": "2026-12-24",
                "source_integrity_status": "LOCAL_METADATA_PINS_MATCH_NOT_CURRENT_AUTHORITY",
                "source_sha256": "a" * 64,
                "official_link_format_checked_only":
                    "https://www.federalregister.gov/documents/2026/10/28/2026-21995/test",
            }],
            "correction_candidates_research_only": [{
                "correcting_document_number": "2026-21995",
                "earlier_document_number": "2026-19391",
                "evidence_status": "PROPOSED_RESEARCH_ONLY",
            }],
            "as_of_calendar_date": "2026-10-28",
            "human_review_checklist": [
                {"check_id": key, "status": "PENDING_HUMAN_REVIEW"}
                for key, _ in audit_packet.CHECKS
            ],
            "external_release_authorized": False,
            "human_review_complete": False,
            "applicability_status": "NOT_DETERMINED",
            "compliance_status": "NOT_DETERMINED",
            "review_disposition": "HOLD_FOR_HUMAN_REVIEW",
        }
        self.save()

    def save(self):
        self.data.pop("audit_sha256", None)
        self.data["audit_sha256"] = audit_packet._sha(self.data)
        self.packet.write_text(json.dumps(self.data), encoding="utf-8")

    def test_packet_only_is_pending(self):
        preview = demo_brief.build_preview(self.packet)
        self.assertEqual(preview["checks"][0]["state"], "PENDING_HUMAN_REVIEW")
        self.assertFalse(preview["external_release_authorized"])

    def test_existing_journal_and_privacy(self):
        review_journal.record_check(
            self.packet, self.journal, check_id="source_text",
            status="CHECKED_RESEARCH_ONLY",
            reviewer="SECRET NAME", reviewer_role="SECRET ROLE",
            notes="SECRET RESEARCH NOTES — I checked this published example",
            citation="https://www.federalregister.gov/documents/test",
            attest=True)
        preview = demo_brief.build_preview(self.packet, self.journal)
        html = demo_brief.render_html(preview)
        self.assertEqual(preview["checks"][0]["state"], "CHECKED_RESEARCH_ONLY")
        self.assertNotIn("SECRET NAME", html)
        self.assertNotIn("SECRET ROLE", html)
        self.assertNotIn("SECRET RESEARCH NOTES", html)
        self.assertIn("Unresolved: 7", html)

    def test_forged_packet_rejected(self):
        self.data["research_candidate"]["subject_label"] = "Modified"
        self.packet.write_text(json.dumps(self.data))
        with self.assertRaises(ValueError):
            demo_brief.build_preview(self.packet)

    def test_real_customer_subject_rejected(self):
        self.data["research_candidate"]["subject_id"] = "customer:42"
        self.data["research_candidate"]["subject_label"] = "Actual Facility"
        self.save()
        with self.assertRaises(ValueError):
            demo_brief.build_preview(self.packet)

    def test_untrusted_link_not_rendered(self):
        self.data["published_metadata_documents"][0]["official_link_format_checked_only"] = (
            "https://phishing.example/test"
        )
        self.save()
        html = demo_brief.render_html(demo_brief.build_preview(self.packet))
        self.assertIn("Official link unavailable", html)
        self.assertNotIn("phishing.example", html)

    def test_xss_html_escaped(self):
        self.data["research_candidate"]["rationale"] = "<script>alert(1)</script>"
        self.save()
        html = demo_brief.render_html(demo_brief.build_preview(self.packet))
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("<script>alert", html)
        self.assertIn("default-src", html)

    def test_source_not_modified(self):
        original = self.packet.read_bytes()
        demo_brief.write_demo(self.packet, None, self.out)
        self.assertEqual(self.packet.read_bytes(), original)
        self.assertTrue(self.out.exists())

    def test_no_overwrite(self):
        self.out.write_text("existing")
        with self.assertRaises(FileExistsError):
            demo_brief.write_demo(self.packet, None, self.out)
        self.assertEqual(self.out.read_text(), "existing")

    def test_no_unauthorized_state(self):
        data = demo_brief.build_preview(self.packet)
        data["external_release_authorized"] = True
        with self.assertRaises(ValueError):
            demo_brief.render_html(data)

    def test_cli(self):
        self.assertEqual(demo_brief.main([
            "--packet", str(self.packet),
            "--out-html", str(self.out)]), 0)
        self.assertIn("INTERNAL DEMO ONLY", self.out.read_text())


if __name__ == "__main__":
    unittest.main()
