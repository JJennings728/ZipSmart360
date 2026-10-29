"""Phase 20 trust boundaries and preservation checks."""
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import unittest
from src.aerocie import customer_report as cr, review_journal


class CustomerReportTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        samples = Path(__file__).resolve().parents[1] / "sample-data" / "phase20"
        for name in ("intake.json", "packet.json"):
            shutil.copyfile(samples / name, self.root / name)
        self.intake = self.root / "intake.json"
        self.packet = self.root / "packet.json"
        self.out = self.root / "result"

    def change(self, **fields):
        value = json.loads(self.intake.read_text())
        value.update(fields)
        self.intake.write_text(json.dumps(value), encoding="utf-8")

    def test_report_preserves_sources_and_holds_release(self):
        before = [p.read_bytes() for p in (self.intake, self.packet)]
        cr.write_report(self.intake, self.packet, None, self.out)
        result = json.loads((self.out / "report.json").read_text())
        self.assertFalse(result["external_release_authorized"])
        self.assertEqual(result["evidence"]["compliance_status"], "NOT_DETERMINED")
        self.assertIn("Official link unavailable", (self.out / "report.html").read_text())
        self.assertNotIn('href="https://www.federalregister.gov/documents/2000',
                         (self.out / "report.html").read_text())
        self.assertEqual(before, [p.read_bytes() for p in (self.intake, self.packet)])

    def test_synthetic_source_is_not_clickable(self):
        report = cr.build_report(self.intake, self.packet)
        self.assertIsNone(report["evidence"]["documents"][0]["url"])
        html = cr.render_report(report)
        self.assertIn("Official link unavailable", html)
        self.assertNotIn('href="https://www.federalregister.gov/documents/2000', html)

    def test_intake_section_follows_header(self):
        html = cr.render_report(cr.build_report(self.intake, self.packet))
        self.assertLess(html.index("</header>"), html.index("Customer intake workflow"))
        self.assertLess(html.index("Customer intake workflow"), html.index("</body>"))

    def test_real_or_extra_fields_rejected(self):
        original = self.intake.read_bytes()
        for update in ({"synthetic": False}, {"synthetic": "true"},
                       {"organization": "Actual Operator"}, {"email": "person@example.test"}):
            with self.subTest(update=update):
                self.intake.write_bytes(original)
                self.change(**update)
                with self.assertRaises(ValueError):
                    cr.write_report(self.intake, self.packet, None, self.out)
                self.assertFalse(self.out.exists())

    def test_subject_mismatch_rejected(self):
        self.change(subject_id="demo:other")
        with self.assertRaises(ValueError):
            cr.build_report(self.intake, self.packet)

    def test_tampered_evidence_rejected(self):
        self.packet.write_text(self.packet.read_text().replace("Synthetic aviation", "Altered aviation"))
        with self.assertRaises(ValueError):
            cr.write_report(self.intake, self.packet, None, self.out)
        self.assertFalse(self.out.exists())

    def test_no_overwrite(self):
        self.out.mkdir()
        marker = self.out / "report.html"
        marker.write_text("keep")
        with self.assertRaises(FileExistsError):
            cr.write_report(self.intake, self.packet, None, self.out)
        self.assertEqual(marker.read_text(), "keep")

    def test_escaped_intake(self):
        self.change(requested_scope='<script>alert("x")</script>')
        html = cr.render_report(cr.build_report(self.intake, self.packet))
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_journal_unchanged_and_private_text_omitted(self):
        journal = self.root / "journal.sqlite3"
        review_journal.record_check(self.packet, journal, check_id="source_text",
            status="FOLLOW_UP_REQUIRED", reviewer="PRIVATE REVIEWER", reviewer_role="PRIVATE ROLE",
            notes="PRIVATE NOTES fixture review only", citation="PRIVATE CITATION", attest=True)
        original = journal.read_bytes()
        cr.write_report(self.intake, self.packet, journal, self.out)
        self.assertEqual(journal.read_bytes(), original)
        for name in ("report.html", "report.json"):
            self.assertNotIn("PRIVATE", (self.out / name).read_text())

    def test_cli(self):
        self.assertEqual(cr.main(["--intake", str(self.intake), "--packet", str(self.packet),
                                  "--out-dir", str(self.out)]), 0)

    def test_release_escalation_rejected(self):
        report = cr.build_report(self.intake, self.packet)
        report["external_release_authorized"] = True
        with self.assertRaises(ValueError):
            cr.render_report(report)

    def test_utf8_bom_intake(self):
        content = self.intake.read_text()
        self.intake.write_text(content, encoding="utf-8-sig")
        cr.build_report(self.intake, self.packet)
