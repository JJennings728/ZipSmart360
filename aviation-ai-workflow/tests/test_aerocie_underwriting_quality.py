"""Phase 25: audit, evidence completeness and data lineage controls."""
from __future__ import annotations

import csv
import hashlib
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest

from src.aerocie import underwriting_pipeline as pipeline
from src.aerocie import underwriting_preview, underwriting_quality as quality


class UnderwritingQualityTests(unittest.TestCase):
    def setUp(self):
        t = TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root = Path(t.name)
        self.db = self.root / "model.db"
        pipeline.create_db(self.db)

    def _mutate(self, statement: str, params: tuple = ()):
        with sqlite3.connect(self.db) as con:
            con.execute(statement, params)
            con.commit()

    def test_all_nine_local_fingerprints_match_original(self):
        before = hashlib.sha256(self.db.read_bytes()).hexdigest()
        audit = quality.audit_database(self.db)
        self.assertEqual(audit["quality_gate"], "INTERNAL_DEMO_ONLY")
        self.assertEqual(audit["summary"]["source_fingerprints_matched"], 4)
        self.assertEqual(audit["summary"]["dimension_fingerprints_matched"], 5)
        self.assertEqual(audit["summary"]["inputs_present"], 5)
        self.assertEqual(audit["summary"]["referred_for_missing_evidence"], 2)
        self.assertEqual(audit["summary"]["blocked_submissions"], 0)
        self.assertEqual(before, hashlib.sha256(self.db.read_bytes()).hexdigest())
        self.assertFalse(audit["external_release_authorized"])
        self.assertEqual(audit["predicted_loss_accuracy"], "NOT_CALIBRATED")

    def test_report_and_powerbi_import_include_quality_panel(self):
        html = underwriting_preview.render(self.db)
        self.assertIn("Integrity checks and evidence gaps", html)
        self.assertIn("Local fingerprints matched", html)
        self.assertIn("MRO_COVERAGE_MISSING", html)
        self.assertIn("7", html)
        result = pipeline.export_tables(self.db, self.root / "export")
        self.assertTrue(result["synthetic_only"])
        self.assertTrue((self.root / "export" / "quality_audit.json").is_file())
        with (self.root / "export" / "submission_quality.csv").open(
                encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 7)
        self.assertEqual(rows[5]["quality_status"], "REFER_FOR_REVIEW")
        self.assertEqual(rows[0]["quality_status"], "INPUTS_PRESENT_SYNTHETIC")

    def test_changed_mro_wait_is_blocked_before_export_and_render(self):
        self._mutate("UPDATE fact_mro_constraints SET repair_wait_days=repair_wait_days+8 WHERE constraint_id='M-001'")
        audit = quality.audit_database(self.db)
        self.assertEqual(audit["quality_gate"], "BLOCKED")
        self.assertIn("SOURCE_FINGERPRINT_MISMATCH", audit["source_checks"][0]["issues"])
        with self.assertRaises(ValueError):
            underwriting_preview.render(self.db)
        with self.assertRaises(ValueError):
            pipeline.export_tables(self.db, self.root / "export")
        self.assertFalse((self.root / "export").exists())

    def test_changed_aircraft_dimension_is_detected(self):
        self._mutate("UPDATE dim_aircraft SET year_built=1999 WHERE aircraft_id='A001'")
        a = quality.audit_database(self.db)
        self.assertEqual(a["quality_gate"], "BLOCKED")
        self.assertTrue(any("DIMENSION_FINGERPRINT_MISMATCH" in d["issues"] for d in a["dimension_checks"]))
        with self.assertRaises(ValueError):
            underwriting_preview.render(self.db)

    def test_changed_model_policy_fails(self):
        self._mutate("UPDATE model_policy SET quote_max_risk_points=90")
        a = quality.audit_database(self.db)
        self.assertEqual(a["policy_check"]["status"], "BLOCKED")
        self.assertEqual(a["quality_gate"], "BLOCKED")
        with self.assertRaises(ValueError):
            pipeline.export_tables(self.db, self.root / "export")

    def test_changed_registry_hash_is_detected(self):
        self._mutate("UPDATE source_registry SET payload_sha256=? WHERE source_id='SRC-NTSB'", ("a"*64,))
        a = quality.audit_database(self.db)
        self.assertEqual(a["quality_gate"], "BLOCKED")
        self.assertEqual(a["source_checks"][2]["dataset"], "NTSB")
        self.assertIn("SOURCE_FINGERPRINT_MISMATCH", a["source_checks"][2]["issues"])

    def test_unknown_additional_registry_entry_blocks(self):
        self._mutate("INSERT INTO source_registry VALUES (?,?,?,?,?,?,?,?,?)",
                     ("SRC-UNKNOWN", "Synthetic unknown", "unknown", None, "2026-10-29",
                      "2026-10-29T12:00:00+00:00", "a"*64, "SYNTHETIC_ONLY", 1))
        a = quality.audit_database(self.db)
        self.assertEqual(a["quality_gate"], "BLOCKED")
        self.assertTrue(any(s["source_id"] == "UNEXPECTED_REGISTRY_ENTRIES" for s in a["source_checks"]))

    def test_future_airframe_never_produces_quote(self):
        fixture = pipeline.synthetic_fixture()
        rec = list(fixture["aircraft"][0]); rec[5] = 2030
        fixture["aircraft"][0] = tuple(rec)
        path = self.root / "future.db"
        pipeline.create_db(path, fixture=fixture)
        with sqlite3.connect(path) as con:
            decision = con.execute("SELECT triage_recommendation, risk_points FROM v_submission_triage WHERE submission_id='S001'").fetchone()
        self.assertEqual(decision, ("Refer", None))
        a = quality.audit_database(path)
        self.assertEqual(a["quality_gate"], "BLOCKED")
        self.assertIn("AIRCRAFT_BUILT_AFTER_SUBMISSION", a["submissions"][0]["issue_codes"])

    def test_contradictory_pilot_hours_never_produces_quote(self):
        fixture = pipeline.synthetic_fixture()
        rec = list(fixture["pilots"][0]); rec[3] = rec[2]+1
        fixture["pilots"][0] = tuple(rec)
        path = self.root / "pilot.db"
        pipeline.create_db(path, fixture=fixture)
        a = quality.audit_database(path)
        self.assertEqual(a["quality_gate"], "BLOCKED")
        self.assertIn("PILOT_HOURS_CONTRADICTORY", a["submissions"][0]["issue_codes"])
        self.assertEqual(a["submissions"][0]["research_label"], "Refer")

    def test_missing_hull_value_requires_referral(self):
        fixture = pipeline.synthetic_fixture()
        rec = list(fixture["submissions"][0]); rec[7] = None
        fixture["submissions"][0] = tuple(rec)
        path = self.root / "missing-hull.db"
        pipeline.create_db(path, fixture=fixture)
        a = quality.audit_database(path)
        self.assertEqual(a["quality_gate"], "INTERNAL_DEMO_ONLY")
        self.assertIn("HULL_VALUE_MISSING_FOR_SEVERITY", a["submissions"][0]["issue_codes"])
        self.assertEqual(a["submissions"][0]["research_label"], "Refer")
        self.assertIsNone(a["submissions"][0]["risk_points"])

    def test_stale_mro_at_import_has_referral_reasons(self):
        fixture = pipeline.synthetic_fixture()
        fixture["mro"] = [tuple(list(r[:4])+["2026-08-20"]+list(r[5:]))
                          if r[2:4] == ("Cessna", "172S") else r for r in fixture["mro"]]
        path = self.root / "stale.db"
        pipeline.create_db(path, fixture=fixture)
        a = quality.audit_database(path)
        self.assertEqual(a["quality_gate"], "INTERNAL_DEMO_ONLY")
        self.assertIn("MRO_OBSERVATION_STALE", a["submissions"][0]["issue_codes"])
        self.assertEqual(a["submissions"][0]["research_label"], "Refer")

    def test_invalid_date_is_detected(self):
        fixture = pipeline.synthetic_fixture()
        rec = list(fixture["submissions"][0]); rec[1] = "2026-02-30"
        fixture["submissions"][0] = tuple(rec)
        path = self.root / "bad-date.db"
        pipeline.create_db(path, fixture=fixture)
        a = quality.audit_database(path)
        self.assertEqual(a["quality_gate"], "BLOCKED")
        self.assertIn("INVALID_SUBMISSION_DATE", a["submissions"][0]["issue_codes"])
        with self.assertRaises(ValueError):
            underwriting_preview.render(path)

    def test_audit_cli_writes_blocked_diagnostics_without_overwrite(self):
        out = self.root / "quality.json"
        self.assertEqual(quality.main(["--db", str(self.db), "--out", str(out)]), 0)
        self.assertIn("source_checks", out.read_text())
        self.assertEqual(quality.main(["--db", str(self.db), "--out", str(out)]), 1)


if __name__ == "__main__":
    unittest.main()
