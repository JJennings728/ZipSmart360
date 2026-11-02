"""Regressions for the read-only AeroCIE export reconciliation gate."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.aerocie import underwriting_pipeline
from src.aerocie.export_reconciliation import reconcile


class ExportReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.db = self.root / "synthetic.db"
        self.folder = self.root / "powerbi-import"
        underwriting_pipeline.create_db(self.db)
        underwriting_pipeline.export_tables(self.db, self.folder)

    def test_untampered_export_reconciles(self):
        report = reconcile(self.folder)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["submission_count"], 7)
        self.assertEqual(report["labels"], {"Decline": 1, "Quote": 2, "Refer": 4})
        self.assertFalse(report["release_authorized"])

    def test_modified_manifested_csv_fails(self):
        with (self.folder / "v_submission_triage.csv").open("a", encoding="utf-8") as file:
            file.write("\n")
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            reconcile(self.folder)

    def test_missing_quality_file_fails(self):
        (self.folder / "submission_quality.csv").unlink()
        with self.assertRaisesRegex(ValueError, "Missing export"):
            reconcile(self.folder)

    def test_quality_label_mismatch_fails(self):
        path = self.folder / "submission_quality.csv"
        with path.open(encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            fields = reader.fieldnames
            rows = list(reader)
        rows[0]["research_label"] = "Decline"
        with path.open("w", encoding="utf-8-sig", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        # Recompute the manifest digest to exercise semantic consistency after the
        # cryptographic integrity gate (a plain tamper is rejected earlier).
        manifest_path = self.folder / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        next(entry for entry in manifest["tables"] if entry["view"] == "submission_quality")["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Triage label disagreement"):
            reconcile(self.folder)

    def test_tampered_quality_status_or_issue_codes_fails_integrity(self):
        path = self.folder / "submission_quality.csv"
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            fields = reader.fieldnames
            rows = list(reader)
        for row in rows:
            row["quality_status"] = "INPUTS_PRESENT_SYNTHETIC"
            row["issue_codes"] = ""
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        with self.assertRaisesRegex(ValueError, "CSV digest mismatch: submission_quality"):
            reconcile(self.folder)


if __name__ == "__main__":
    unittest.main()
