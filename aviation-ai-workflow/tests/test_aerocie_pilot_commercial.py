"""Pilot offer economics and retrospective evaluation safeguards."""
import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from src.aerocie import pilot_evaluation, pilot_economics

DATA=Path(__file__).resolve().parents[1]/"sample-data"/"phase24"

class PilotEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc=json.loads((DATA/'synthetic-pilot-evaluation.json').read_text())
        cls.econ=json.loads((DATA/'pilot-economics-assumptions.json').read_text())

    def test_fifty_cases_and_both_baselines(self):
        r=pilot_evaluation.evaluate(self.doc)
        self.assertEqual(r['cases'],50)
        self.assertEqual(r['known_outcome_cases'],47)
        self.assertEqual(r['unknown_outcome_cases'],3)
        self.assertEqual(r['missing_evidence_cases'],3)
        for field in ('aerocie','baseline'):
            metrics=r[field]
            self.assertEqual(sum(metrics[x] for x in ('true_positive','false_positive','false_negative','true_negative')),47)
            self.assertGreaterEqual(metrics['adverse_case_recall'],0)
        self.assertEqual(len(r['data_sha256']),64)
        self.assertGreater(r['total_minutes_saved'],0)

    def test_missing_evidence_must_refer(self):
        d=copy.deepcopy(self.doc)
        d['cases'][7]['aerocie_label']='Quote'
        with self.assertRaises(ValueError):pilot_evaluation.evaluate(d)

    def test_reject_personal_data_or_extra_fields(self):
        d=copy.deepcopy(self.doc)
        d['cases'][0]['pilot_name']='Private Person'
        with self.assertRaises(ValueError):pilot_evaluation.evaluate(d)

    def test_reject_duplicate_cases(self):
        d=copy.deepcopy(self.doc)
        d['cases'][1]['case_id']=d['cases'][0]['case_id']
        with self.assertRaises(ValueError):pilot_evaluation.evaluate(d)

    def test_reject_false_label_or_outcome(self):
        for field,bad in (('aerocie_label','100%'),('adverse_outcome','False'),('baseline_minutes',-2),('aerocie_minutes',float('inf'))):
            with self.subTest(field=field):
                d=copy.deepcopy(self.doc)
                d['cases'][0][field]=bad
                with self.assertRaises(ValueError):pilot_evaluation.evaluate(d)

    def test_no_real_case_mode_in_synthetic_validator(self):
        d=copy.deepcopy(self.doc); d['synthetic']=False
        with self.assertRaises(ValueError):pilot_evaluation.evaluate(d)

    def test_no_outcome_unknown_does_not_count_as_negative(self):
        d=copy.deepcopy(self.doc)
        for c in d['cases']:c['adverse_outcome']=None
        r=pilot_evaluation.evaluate(d)
        self.assertIsNone(r['aerocie']['positive_predictive_value'])
        self.assertIsNone(r['aerocie']['adverse_case_recall'])
        self.assertEqual(r['known_outcome_cases'],0)

    def test_evaluation_cli_does_not_overwrite(self):
        with TemporaryDirectory() as t:
            input_=DATA/'synthetic-pilot-evaluation.json';out=Path(t)/'report.json'
            self.assertEqual(pilot_evaluation.main(['--input',str(input_),'--out',str(out)]),0)
            self.assertEqual(pilot_evaluation.main(['--input',str(input_),'--out',str(out)]),1)

    def test_economics_calculator_gross_and_net(self):
        r=pilot_economics.calculate(self.econ)
        self.assertEqual(r['monthly_submission_volume'],100)
        self.assertAlmostEqual(r['net_monthly_hours_saved'],41.67,places=2)
        self.assertEqual(r['annual_subscription_revenue_to_srp_usd'],60000)
        self.assertLess(r['monthly_net_operational_value_usd'],0)
        self.assertEqual(r['monthly_submissions_for_labor_only_break_even'],213)

    def test_economics_keeps_negative_savings(self):
        d=dict(self.econ);d['baseline_minutes_per_submission']=4;d['aerocie_minutes_per_submission']=10
        r=pilot_economics.calculate(d)
        self.assertLess(r['net_monthly_hours_saved'],0)

    def test_economics_rejects_bad_inputs(self):
        for key, bad in [('monthly_submissions',1.3),('monthly_submissions',True),('monthly_subscription_usd',-1),('loaded_hourly_analyst_cost_usd','NaN'),('aerocie_minutes_per_submission','Infinity')]:
            with self.subTest(key=key):
                d=dict(self.econ);d[key]=bad
                with self.assertRaises(ValueError):pilot_economics.calculate(d)

    def test_economics_cli_is_no_overwrite(self):
        with TemporaryDirectory() as t:
            source=DATA/'pilot-economics-assumptions.json';out=Path(t)/'roi.json'
            self.assertEqual(pilot_economics.main(['--assumptions',str(source),'--out',str(out)]),0)
            self.assertEqual(pilot_economics.main(['--assumptions',str(source),'--out',str(out)]),1)

if __name__=='__main__':unittest.main()
