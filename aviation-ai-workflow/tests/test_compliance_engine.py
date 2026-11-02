"""Run: python -m unittest discover -s tests -p 'test_compliance_engine.py' -v"""
import importlib.util
import unittest
from pathlib import Path

root = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location("compliance_engine", root / "src" / "compliance_engine.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class ComplianceEngineTests(unittest.TestCase):
    def setUp(self):
        self.payload = {
            "organization": "Synthetic aviation operator",
            "sources": [{"id": "S1", "title": "Synthetic Rule", "url": "https://example.org/rule",
                         "jurisdiction": "TEST", "accessed_utc": "2026-10-18T00:00:00Z", "reviewer_verified": True}],
            "evidence": [{"id": "E1", "description": "Synthetic governance record"}],
            "controls": [{"id": "C1", "question": "Is documentation available?", "source_ids": ["S1"],
                          "evidence_ids": ["E1"], "applicability": "human_confirmed_applicable"}],
        }

    def test_never_certifies_compliance(self):
        r = mod.analyze(self.payload)
        self.assertEqual(r["regulatory_compliance_determination"], "NOT_DETERMINED")
        self.assertTrue(r["human_review_required"])
        self.assertEqual(r["controls"][0]["triage_status"], "ready_for_human_review")

    def test_missing_evidence_and_unverified_source(self):
        self.payload["controls"][0]["evidence_ids"] = []
        self.payload["sources"][0]["reviewer_verified"] = False
        r = mod.analyze(self.payload)
        self.assertIn("NO_EVIDENCE_MAPPED", r["controls"][0]["flags"])
        self.assertIn("SOURCE_NOT_HUMAN_VERIFIED:S1", r["controls"][0]["flags"])
        self.assertEqual(r["summary"]["needs_documentation"], 1)

    def test_unknown_source_and_applicability(self):
        self.payload["controls"][0]["source_ids"] = ["S404"]
        del self.payload["controls"][0]["applicability"]
        flags = mod.analyze(self.payload)["controls"][0]["flags"]
        self.assertIn("UNKNOWN_SOURCE:S404", flags)
        self.assertIn("APPLICABILITY_NOT_HUMAN_CONFIRMED", flags)

    def test_invalid_duplicate_ids(self):
        self.payload["sources"].append(dict(self.payload["sources"][0]))
        with self.assertRaisesRegex(ValueError, "Duplicate sources IDs"):
            mod.analyze(self.payload)

    def test_invalid_input(self):
        with self.assertRaises(ValueError):
            mod.analyze([])


if __name__ == "__main__":
    unittest.main()
