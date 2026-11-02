"""Static regression for Power BI TMDL table description syntax.

Power BI Desktop is the authoritative runtime parser; this checks a known
invalid form so it cannot be reintroduced unnoticed.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "powerbi" / "AeroCIE-Underwriting.SemanticModel" / "definition"
TABLES = MODEL / "tables"


class TmdlDescriptionTests(unittest.TestCase):
    def test_every_referenced_table_has_supported_description_syntax(self):
        model = (MODEL / "model.tmdl").read_text(encoding="utf-8")
        references = re.findall(r"^ref table (\S+)$", model, flags=re.MULTILINE)
        self.assertTrue(references)
        self.assertEqual(len(references), len(set(references)))
        for name in references:
            with self.subTest(table=name):
                contents = (TABLES / f"{name}.tmdl").read_text(encoding="utf-8")
                self.assertTrue(contents.startswith("/// "), name)
                self.assertRegex(contents, rf"(?m)^table {re.escape(name)}$")
                self.assertNotRegex(contents, r"(?m)^\s+description:\s")

    def test_all_table_files_avoid_unsupported_description_property(self):
        files = list(TABLES.glob("*.tmdl"))
        self.assertTrue(files)
        for file in files:
            with self.subTest(file=file.name):
                contents = file.read_text(encoding="utf-8")
                self.assertNotRegex(contents, r"(?m)^\s+description:\s")


if __name__ == "__main__":
    unittest.main()
