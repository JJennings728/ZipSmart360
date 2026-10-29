"""AeroCIE phase 24 regression tests: synthetic intake/MRO/triage, integrity and exports."""
from __future__ import annotations
import csv
import hashlib
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from src.aerocie import underwriting_pipeline as pipeline, underwriting_preview

class UnderwritingPipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.db=self.root/'underwriting.db'
        self.result=pipeline.create_db(self.db)

    def con(self):
        return sqlite3.connect(self.db)

    def test_database_has_normalized_schema_and_source_ids(self):
        with self.con() as c:
            tables={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertTrue({'dim_aircraft','dim_pilot','dim_mro_facility','fact_mro_constraints',
                             'fact_underwriting_submissions','fact_ntsb_model_context','fact_swim_operations','source_registry','model_policy'}<=tables)
            self.assertEqual(c.execute('PRAGMA foreign_key_check').fetchall(),[])
            self.assertEqual(c.execute('SELECT count(*) FROM source_registry WHERE is_synthetic=0').fetchone()[0],0)

    def test_fixed_seed_reproducible(self):
        self.assertEqual(pipeline._hash(pipeline.synthetic_fixture()),self.result['fixture_hash'])
        self.assertEqual(self.result['fixture_hash'],pipeline._hash(pipeline.synthetic_fixture()))

    def test_all_three_advisory_states_present(self):
        with self.con() as c:
            states={x[0] for x in c.execute('SELECT DISTINCT triage_recommendation FROM v_submission_triage')}
        self.assertEqual(states,{'Quote','Refer','Decline'})

    def test_incomplete_evidence_returns_refer_and_null(self):
        with self.con() as c:
            rows=c.execute("SELECT submission_id,risk_points,triage_recommendation,insufficient_evidence FROM v_submission_triage WHERE submission_id IN ('S006','S007') ORDER BY submission_id").fetchall()
        self.assertEqual([x[1:] for x in rows],[(None,'Refer',1),(None,'Refer',1)])

    def test_decline_label_never_auto_binds(self):
        with self.con() as c:
            r=c.execute("SELECT triage_recommendation,decision_authority,risk_points FROM v_submission_triage WHERE submission_id='S003'").fetchone()
            approved=c.execute('SELECT approved_for_automatic_binding FROM model_policy').fetchone()[0]
        self.assertEqual(r[0],'Decline');self.assertGreaterEqual(r[2],70)
        self.assertEqual(r[1],'UNDERWRITER_REVIEW_REQUIRED');self.assertEqual(approved,0)

    def test_explanation_points_sum_to_risk(self):
        with self.con() as c:
            r=c.execute("SELECT risk_points,age_points,total_time_points,type_time_points,loss_points,mro_points,composite_points,training_points FROM v_submission_triage WHERE submission_id='S005'").fetchone()
        self.assertEqual(r[0],min(100,sum(r[1:])))

    def test_old_mro_data_requires_referral(self):
        with self.con() as c:
            c.execute("UPDATE fact_mro_constraints SET as_of='2026-01-01' WHERE manufacturer='Cessna' AND model='172S'")
            c.commit()
            decision=c.execute("SELECT insufficient_evidence,triage_recommendation,risk_points FROM v_submission_triage WHERE submission_id='S001'").fetchone()
        self.assertEqual(decision,(1,'Refer',None))

    def test_stale_mro_snapshot_ignored(self):
        with self.con() as c:
            rows=c.execute("SELECT constraint_id FROM v_mro_latest WHERE manufacturer='Cessna' AND model='172S' AND facility_id='F001'").fetchall()
            self.assertNotEqual(rows,[('M-OLD',)])
            self.assertEqual(len(rows),1)

    def test_mro_weighted_severity_matches_formula(self):
        with self.con() as c:
            vals=c.execute("SELECT repair_wait_days,parts_availability_index FROM v_mro_latest WHERE manufacturer='Cessna' AND model='172S'").fetchall()
            actual=c.execute("SELECT mro_severity_days FROM v_mro_model_metrics WHERE manufacturer='Cessna' AND model='172S'").fetchone()[0]
        expected=round(sum(wait*(2-index) for wait,index in vals)/sum(2-index for _,index in vals),2)
        self.assertAlmostEqual(actual,expected,places=2)

    def test_model_has_source_provenance(self):
        with self.con() as c:
            count=c.execute('SELECT count(*) FROM fact_mro_constraints m LEFT JOIN source_registry s ON s.source_id=m.source_id WHERE s.source_id IS NULL').fetchone()[0]
            self.assertEqual(count,0)
            self.assertTrue(all(len(x[0])==64 for x in c.execute('SELECT payload_sha256 FROM source_registry')))

    def test_unknown_model_does_not_get_safe_mro_index(self):
        with self.con() as c:
            rec=c.execute("SELECT mro_severity_days,insufficient_evidence FROM v_submission_triage WHERE submission_id='S006'").fetchone()
        self.assertEqual(rec,(None,1))

    def test_submission_must_have_valid_foreign_key(self):
        with self.con() as c:
            c.execute('PRAGMA foreign_keys=ON')
            with self.assertRaises(sqlite3.IntegrityError):
                c.execute("INSERT INTO fact_underwriting_submissions VALUES ('BAD','2026-10-29','NO_AIRCRAFT',NULL,'PRIVATE',100,0,100000,'SRC-INTAKE')")

    def test_reject_negative_wait_and_bad_availability(self):
        with self.con() as c:
            c.execute('PRAGMA foreign_keys=ON')
            for wait,idx in [(-1,.4),(1,1.1),(1,-.1)]:
                with self.subTest(wait=wait,index=idx):
                    with self.assertRaises(sqlite3.IntegrityError):
                        c.execute("INSERT INTO fact_mro_constraints VALUES ('BAD','F001','Cessna','172S','2026-10-30',?,?,1,'SRC-MRO')",(wait,idx))

    def test_no_database_overwrite(self):
        before=self.db.read_bytes()
        with self.assertRaises(FileExistsError):pipeline.create_db(self.db)
        self.assertEqual(self.db.read_bytes(),before)

    def test_exports_csv_manifest_and_no_overwrite(self):
        folder=self.root/'exports';before=hashlib.sha256(self.db.read_bytes()).hexdigest()
        res=pipeline.export_tables(self.db,folder)
        self.assertEqual(len(res['tables']),len(pipeline.EXPORT_VIEWS))
        with (folder/'v_submission_triage.csv').open(encoding='utf-8-sig',newline='') as f:
            rows=list(csv.DictReader(f))
        self.assertEqual(len(rows),7)
        self.assertIn('risk_points',rows[0]);self.assertIn('mro_severity_days',rows[0])
        with self.assertRaises(FileExistsError):pipeline.export_tables(self.db,folder)
        self.assertEqual(hashlib.sha256(self.db.read_bytes()).hexdigest(),before)

    def test_csv_injection_escaped(self):
        fixture = pipeline.synthetic_fixture()
        row = list(fixture["aircraft"][0])
        row[3] = '=HYPERLINK("http://example.test")'
        fixture["aircraft"][0] = tuple(row)
        prepared = self.root / "prepared-injection.db"
        pipeline.create_db(prepared, fixture=fixture)
        folder = self.root / "export_escaped"
        pipeline.export_tables(prepared, folder)
        with (folder/'v_submission_triage.csv').open(encoding='utf-8-sig',newline='') as f:
            rows=list(csv.DictReader(f))
        self.assertTrue(any(row['model'].startswith("'=") for row in rows))

    def test_preview_renders_html_and_rejects_overwrite(self):
        before=self.db.read_bytes()
        path=self.root/'report.html'
        output=underwriting_preview.write(self.db,path)
        html=path.read_text()
        self.assertFalse(output['external_release_authorized'])
        self.assertIn('STRATEGICRISK PARTNERS',html)
        self.assertIn('MRO severity',html)
        self.assertIn('UNDERWRITER',html.upper())
        with self.assertRaises(ValueError):underwriting_preview.write(self.db,path)
        self.assertEqual(self.db.read_bytes(),before)

    def test_preview_rejects_injected_script(self):
        fixture = pipeline.synthetic_fixture()
        row = list(fixture["aircraft"][0])
        row[3] = "<script>alert(1)</script>"
        fixture["aircraft"][0] = tuple(row)
        prepared = self.root / "prepared-html.db"
        pipeline.create_db(prepared, fixture=fixture)
        html = underwriting_preview.render(prepared)
        self.assertNotIn('<script>alert(1)</script>',html)
        self.assertIn('&lt;script&gt;',html)

if __name__=='__main__':unittest.main()
