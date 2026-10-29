"""Phase 24 validation of scenario sensitivity visuals and source safeguards."""
from pathlib import Path
from tempfile import TemporaryDirectory
import sqlite3
import unittest

from src.aerocie import underwriting_pipeline, underwriting_preview


class SeverityVisualizationTests(unittest.TestCase):
    def setUp(self):
        t=TemporaryDirectory();self.addCleanup(t.cleanup)
        self.db=Path(t.name)/"synthetic.db"
        underwriting_pipeline.create_db(self.db)

    def test_scenarios_have_ordered_bounds_and_source_status(self):
        with sqlite3.connect(self.db) as c:
            rows=c.execute("SELECT scenario_low_usd,scenario_base_usd,scenario_high_usd,scenario_basis,pricing_adequacy_status FROM v_severity_scenarios WHERE scenario_base_usd IS NOT NULL").fetchall()
        self.assertTrue(rows)
        for low,base,high,basis,adequacy in rows:
            self.assertLessEqual(low,base);self.assertLessEqual(base,high)
            self.assertEqual(basis,"SYNTHETIC_ASSUMPTION_NOT_CLAIM_FORECAST")
            self.assertEqual(adequacy,"NOT_DETERMINED_WITHOUT_PREMIUM_AND_VALIDATED_LOSS_MODEL")

    def test_missing_evidence_makes_all_scenarios_null(self):
        with sqlite3.connect(self.db) as c:
            rows=c.execute("SELECT submission_id,scenario_low_usd,scenario_base_usd,scenario_high_usd FROM v_severity_scenarios WHERE submission_id IN ('S006','S007') ORDER BY submission_id").fetchall()
        self.assertEqual(rows,[("S006",None,None,None),("S007",None,None,None)])

    def test_high_scenario_changes_monotonically_with_cost_pressure(self):
        with sqlite3.connect(self.db) as c:
            old=c.execute("SELECT scenario_high_usd FROM v_severity_scenarios WHERE submission_id='S004'").fetchone()[0]
            c.execute("UPDATE fact_mro_constraints SET parts_cost_index=parts_cost_index+0.5 WHERE manufacturer='Gulfstream'")
            new=c.execute("SELECT scenario_high_usd FROM v_severity_scenarios WHERE submission_id='S004'").fetchone()[0]
        self.assertGreater(new,old)

    def test_display_explains_assumptions_and_unknown_pricing_adequacy(self):
        html=underwriting_preview.render(self.db)
        for word in ("Which risks deserve another look", "Repair cost sensitivity", "Low", "premium", "Unknown", "250", "0.50%", "No cost scenario calculated"):
            self.assertIn(word.lower(),html.lower())
        self.assertNotIn("estimated avoided claim",html.lower())
        self.assertIn("Quote review label",html)
        self.assertIn("S004",html)

    def test_exposure_totals_never_called_insured_value(self):
        html=underwriting_preview.render(self.db)
        self.assertIn('Requested hull total | not insured sum',html)
        self.assertIn('price',html.lower())

    def test_all_scenarios_block_after_source_becomes_stale(self):
        with sqlite3.connect(self.db) as c:
            c.execute("UPDATE fact_mro_constraints SET as_of='2025-01-01'")
            result=c.execute("SELECT COUNT(*) FROM v_severity_scenarios WHERE scenario_base_usd IS NOT NULL").fetchone()[0]
        self.assertEqual(result,0)

    def test_html_escapes_untrusted_aircraft_names_in_stress_charts(self):
        fixture = underwriting_pipeline.synthetic_fixture()
        row = list(fixture["aircraft"][0])
        row[3] = '<img src=x onerror=alert(1)>'
        fixture["aircraft"][0] = tuple(row)
        prepared = self.db.parent / "prepared-html.db"
        underwriting_pipeline.create_db(prepared, fixture=fixture)
        html = underwriting_preview.render(prepared)
        self.assertNotIn('<img src=x onerror=alert(1)>',html)
