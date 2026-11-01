"""Static regression checks for documented synthetic Power BI metric definitions."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "powerbi" / "AeroCIE-Underwriting.SemanticModel" / "definition" / "tables"

EXPECTED = {
    "v_submission_triage.tmdl": [
        "Synthetic Submissions", "Advisory Quote", "Advisory Refer",
        "Advisory Decline", "Missing Evidence", "Requested Hull Total Not Insured",
    ],
    "v_severity_scenarios.tmdl": [
        "Scenario Low Synthetic", "Scenario Base Synthetic",
        "Scenario High Synthetic", "Scenario Available Count",
    ],
    "submission_quality.tmdl": ["Evidence Referrals"],
}

class PowerBIMeasureDefinitionTests(unittest.TestCase):
    def test_expected_metric_names_present_without_duplicates(self):
        all_names = []
        for file, expected_names in EXPECTED.items():
            contents = (TABLES / file).read_text(encoding="utf-8")
            names = re.findall(r"^\\tmeasure '([^']+)' = ", contents, flags=re.MULTILINE)
            self.assertEqual(names, expected_names, file)
            all_names.extend(names)
        self.assertEqual(len(all_names), len(set(all_names)))

    def test_metrics_are_labeled_and_exclude_claim_forecasts(self):
        text = "\n".join((TABLES / file).read_text(encoding="utf-8")
                         for file in EXPECTED)
        self.assertIn("Not Insured", text)
        self.assertIn("Synthetic", text)
        self.assertNotIn("Predicted Claims", text)
        self.assertNotIn("Premium Adequacy", text)

    def test_each_measure_has_explicit_format(self):
        for file in EXPECTED:
            contents = (TABLES / file).read_text(encoding="utf-8")
            self.assertEqual(contents.count("\n\tmeasure '"),
                             contents.count("\n\t\tformatString: "))

if __name__ == "__main__":
    unittest.main()
