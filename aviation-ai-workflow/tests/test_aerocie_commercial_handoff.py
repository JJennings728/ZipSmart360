"""AeroCIE-034: end-to-end synthetic underwriting export to internal case brief."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.aerocie.underwriting_pipeline import create_db, export_tables
from src.aerocie.export_reconciliation import reconcile
from src.aerocie.submission_brief import build_brief


class CommercialHandoffTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory(prefix="srp-commercial-handoff-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.db = self.root / "synthetic.sqlite3"
        self.export = self.root / "export"
        create_db(self.db)
        export_tables(self.db, self.export)

    def test_pipeline_exports_exactly_seven_reconciled_synthetic_cases(self):
        result = reconcile(self.export)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["scope"], "SYNTHETIC_INTERNAL_ONLY")
        self.assertEqual(result["submission_count"], 7)
        self.assertEqual(result["labels"], {"Decline": 1, "Quote": 2, "Refer": 4})
        self.assertEqual(result["files_verified_by_sha256"], 10)
        self.assertEqual(result["requested_hull_total_usd_NOT_INSURED_VALUE"], "34045000")
        self.assertEqual([float(v) for v in result["scenario_totals_usd_NOT_CLAIM_FORECAST"]],
                         [46243, 104080, 208159])
        self.assertIs(result["release_authorized"], False)

    def test_internal_case_briefs_reference_actual_synthetic_case_ids(self):
        for cid in ("S001", "S006", "S007"):
            with self.subTest(submission=cid):
                brief = build_brief(self.export, cid)
                self.assertIn(f"AeroCIE submission review | {cid}", brief)
                self.assertIn("Synthetic demonstration | Internal human review only", brief)
                self.assertIn("Evidence follow-up", brief)
                self.assertIn("Intake snapshot SHA-256:", brief)
                self.assertNotIn("coverage bound", brief.lower())

    def test_brief_fails_closed_on_digest_tamper(self):
        source = self.export / "source_registry.csv"
        source.write_bytes(source.read_bytes() + b"\n")
        with self.assertRaisesRegex(ValueError, "CSV digest mismatch"):
            build_brief(self.export, "S007")

    def test_unknown_case_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Expected one"):
            build_brief(self.export, "NONEXISTENT")

    def test_missing_quality_evidence_is_raised_in_brief(self):
        brief = build_brief(self.export, "S007")
        self.assertTrue(any(marker in brief for marker in
                            ("ANNUAL_FLIGHT_HOURS_MISSING", "PILOT_EVIDENCE_MISSING",
                             "MRO_COVERAGE_MISSING", "LOSS_HISTORY_MISSING")))
        self.assertIn("Quality status:", brief)


if __name__ == "__main__":
    unittest.main()
