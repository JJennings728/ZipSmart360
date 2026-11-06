"""Offline defensive checks for synthetic prime SCRM research module."""
from __future__ import annotations

from contextlib import closing
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest

from src.aerocie.prime_pilot import evaluate, main, persist_new

FIXTURE = Path(__file__).resolve().parents[1] / "sample-data" / "prime_scrm_synthetic.json"


class PrimePilotTests(unittest.TestCase):
    def setUp(self):
        self.payload = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_deterministic_and_source_linked(self):
        a, b = evaluate(self.payload), evaluate(deepcopy(self.payload))
        self.assertEqual(a, b)
        self.assertEqual(a["summary"]["components_evaluated"], 3)
        self.assertEqual(a["summary"]["review_flag_count"], 2)
        self.assertEqual(a["summary"]["largest_assumed_critical_component_increase_days"], 30)
        self.assertFalse(a["external_release_authorized"])
        self.assertIn("NOT_AVAILABLE", a["summary"]["schedule_forecast"])
        self.assertEqual(len(a["input_sha256"]), 64)

    def test_refuses_cui_or_non_synthetic(self):
        for invalid in ("CUI", "FCI", "PUBLIC", None):
            test = deepcopy(self.payload)
            test["data_classification"] = invalid
            with self.assertRaises(ValueError):
                evaluate(test)

    def test_refuses_release_or_unpinned_evidence(self):
        for field, value in (("external_release_authorized", True),
                             ("external_release_authorized", None)):
            test = deepcopy(self.payload)
            test[field] = value
            with self.assertRaises(ValueError):
                evaluate(test)
        test = deepcopy(self.payload)
        test["evidence"][0]["text"] += " tampered"
        with self.assertRaisesRegex(ValueError, "fingerprint mismatch"):
            evaluate(test)

    def test_refuses_missing_and_duplicate_references(self):
        for field, value in (("supplier_id", "unknown"), ("evidence_id", "unknown")):
            test = deepcopy(self.payload)
            test["components"][0][field] = value
            with self.assertRaisesRegex(ValueError, "Unresolved"):
                evaluate(test)
        test = deepcopy(self.payload)
        test["components"].append(deepcopy(test["components"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            evaluate(test)

    def test_refuses_unsafe_numeric_and_flags(self):
        for value in (-1, 1.2, True, "30", 5000):
            test = deepcopy(self.payload)
            test["components"][0]["scenario_lead_days"] = value
            with self.assertRaises(ValueError):
                evaluate(test)
        test = deepcopy(self.payload)
        test["components"][0]["critical_path_assumed"] = "yes"
        with self.assertRaises(ValueError):
            evaluate(test)

    def test_sqlite_and_no_overwrite(self):
        report = evaluate(self.payload)
        with TemporaryDirectory() as temp:
            db = Path(temp) / "screens.db"
            persist_new(db, report)
            with closing(sqlite3.connect(db)) as con:
                self.assertEqual(con.execute("SELECT COUNT(*) FROM reports").fetchone()[0], 1)
                self.assertEqual(con.execute("SELECT COUNT(*) FROM component_screen").fetchone()[0], 3)
            with self.assertRaises(FileExistsError):
                persist_new(db, report)

    def test_cli_writes_explicit_output(self):
        with TemporaryDirectory() as temp:
            out = Path(temp) / "report.json"
            db = Path(temp) / "report.db"
            self.assertEqual(main(["--input", str(FIXTURE), "--out", str(out), "--db", str(db)]), 0)
            report = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "INTERNAL_SYNTHETIC_ONLY")
            self.assertTrue(db.is_file())
            self.assertEqual(len(report["report_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
