"""AeroCIE-017: synthetic print report and evidence-control regressions."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.aerocie import pilot_report, review_journal


class PilotReportTests(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.data = Path(__file__).resolve().parents[1] / "sample-data" / "phase20"
        self.intake = self.root / "intake.json"
        self.packet = self.root / "packet.json"
        self.intake.write_bytes((self.data / "intake.json").read_bytes())
        self.packet.write_bytes((self.data / "packet.json").read_bytes())
        self.out = self.root / "pilot.html"

    def test_synthetic_report_has_research_only_labels(self):
        report = pilot_report.make_model(self.intake, self.packet)
        self.assertEqual(report["counts"]["unresolved_review_checks"], 8)
        self.assertFalse(report["external_release_authorized"])
        html = pilot_report.render_html(report)
        for token in ("NOT FOR CLIENT RELEASE", "NOT DETERMINED", "Synthetic",
                      "CHECKS RECORDED", "Human verification checklist", "@media print"):
            self.assertIn(token, html)
        self.assertIn("HOLD FOR HUMAN REVIEW", html)

    def test_no_fake_official_link(self):
        html = pilot_report.render_html(pilot_report.make_model(self.intake, self.packet))
        self.assertIn("Not available / not verified", html)
        self.assertNotIn('href="https://www.federalregister.gov/documents/2000', html)

    def test_xss_in_requested_scope_escaped(self):
        obj = json.loads(self.intake.read_text())
        obj["requested_scope"] = '<script>alert("x")</script>'
        self.intake.write_text(json.dumps(obj))
        html = pilot_report.render_html(pilot_report.make_model(self.intake, self.packet))
        self.assertNotIn('<script>alert("x")</script>', html)
        self.assertIn('&lt;script&gt;', html)

    def test_validity_guards_reject_release_flags(self):
        for key, value in (("external_release_authorized", True),
                           ("release_status", "APPROVED"),
                           ("compliance_status", "COMPLIANT"),
                           ("applicability_status", "APPLICABLE"),
                           ("internal_only", False)):
            with self.subTest(key=key):
                report = pilot_report.make_model(self.intake, self.packet)
                report[key] = value
                with self.assertRaises(ValueError):
                    pilot_report.render_html(report)

    def test_reviewer_names_notes_and_citations_excluded(self):
        journal = self.root / "journal.sqlite3"
        review_journal.record_check(self.packet, journal,
            check_id="source_text", status="FOLLOW_UP_REQUIRED",
            reviewer="PRIVATE_TEST_REVIEWER", reviewer_role="PRIVATE_TEST_ROLE",
            notes="PRIVATE_TEST_RESEARCH_NOTES need independent checks",
            citation="PRIVATE_TEST_CITATION", attest=True)
        model = pilot_report.make_model(self.intake, self.packet, journal)
        self.assertEqual(model["counts"]["unresolved_review_checks"], 8)
        output = pilot_report.render_html(model)
        for private in ("PRIVATE_TEST_REVIEWER", "PRIVATE_TEST_ROLE",
                        "PRIVATE_TEST_RESEARCH_NOTES", "PRIVATE_TEST_CITATION"):
            self.assertNotIn(private, output)

    def test_unchecked_review_state_does_not_hide_pending_items(self):
        model = pilot_report.make_model(self.intake, self.packet)
        model["checks"][0]["state"] = "FAKE_APPROVED"
        with self.assertRaises(ValueError):
            pilot_report.render_html(model)

    def test_count_inconsistency_rejected(self):
        model = pilot_report.make_model(self.intake, self.packet)
        model["counts"]["unresolved_review_checks"] = 0
        with self.assertRaises(ValueError):
            pilot_report.render_html(model)

    def test_no_overwrite_existing_html(self):
        self.out.write_text("existing")
        with self.assertRaises(FileExistsError):
            pilot_report.write_preview(self.intake, self.packet, None, self.out)
        self.assertEqual(self.out.read_text(), "existing")

    def test_no_input_modification(self):
        hashes = [p.read_bytes() for p in (self.packet, self.intake)]
        pilot_report.write_preview(self.intake, self.packet, None, self.out)
        self.assertEqual(hashes, [p.read_bytes() for p in (self.packet, self.intake)])
        self.assertTrue(self.out.is_file())

    def test_invalid_subject_refused(self):
        obj = json.loads(self.intake.read_text())
        obj["subject_id"] = "client:facility"
        self.intake.write_text(json.dumps(obj))
        with self.assertRaises(ValueError):
            pilot_report.make_model(self.intake, self.packet)

    def test_tampered_packet_refused(self):
        self.packet.write_text(self.packet.read_text().replace("Synthetic aviation", "Altered aviation"))
        with self.assertRaises(ValueError):
            pilot_report.write_preview(self.intake, self.packet, None, self.out)
        self.assertFalse(self.out.exists())

    def test_cli_returns_success_and_writes_report(self):
        self.assertEqual(pilot_report.main(["--intake", str(self.intake),
            "--packet", str(self.packet), "--out-html", str(self.out)]), 0)
        self.assertIn("Aviation Regulatory", self.out.read_text())

    def test_reject_output_on_packet_path(self):
        with self.assertRaises(ValueError):
            pilot_report.write_preview(self.intake, self.packet, None, self.packet)

    def test_safe_link_presentation_allowlist(self):
        self.assertIn('Open published source', pilot_report._link(
            'https://www.federalregister.gov/documents/2026/10/28/2026-21995/example'))
        self.assertNotIn('href=', pilot_report._link('https://attacker.example/doc'))


if __name__ == "__main__":
    unittest.main()
