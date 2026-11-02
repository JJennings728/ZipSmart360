"""Static safeguards against invalid TMDL multi-line DAX indentation.

A passing test is NOT a replacement for parsing the semantic model in
Power BI Desktop or for evaluating DAX against imported data.
"""
from pathlib import Path
import re
import unittest


TABLES = (
    Path(__file__).resolve().parents[1]
    / "powerbi"
    / "AeroCIE-Underwriting.SemanticModel"
    / "definition"
    / "tables"
)


class PowerBIMultilineDAXTests(unittest.TestCase):
    def test_multiline_dax_is_nested_at_expression_indentation(self):
        count = 0
        for path in TABLES.glob("*.tmdl"):
            lines = path.read_text(encoding="utf-8").splitlines()
            for idx, line in enumerate(lines):
                if not re.match(r"^\tmeasure [^=]+ =\s*$", line):
                    continue
                count += 1
                self.assertLess(idx + 1, len(lines), path.name)
                self.assertTrue(
                    lines[idx + 1].startswith("\t\t\t"),
                    f"{path.name}:{idx + 2} DAX must be indented at least three tabs",
                )
                following = idx + 1
                while following < len(lines):
                    next_line = lines[following]
                    if next_line.startswith("\tmeasure ") or next_line.startswith("\tpartition "):
                        break
                    if next_line.strip() and not next_line.startswith("\t\t"):
                        self.fail(f"{path.name}:{following + 1} unexpected measure indentation")
                    if re.match(r"^\t\t(?:VAR|RETURN)\b", next_line, re.IGNORECASE):
                        self.fail(f"{path.name}:{following + 1} DAX parsed as property")
                    following += 1
        self.assertGreaterEqual(count, 3)

    def test_complex_measures_use_multiline_declarations(self):
        content = (TABLES / "v_submission_features.tmdl").read_text(encoding="utf-8")
        for name in ("MRO_Severity_Index", "Triage_Risk_Points", "Automated_Triage_Status"):
            self.assertIn(f"\tmeasure {name} =\n\t\t\tVAR ", content)
            self.assertNotRegex(content, rf"(?m)^\tmeasure {name} = VAR ")


if __name__ == "__main__":
    unittest.main()
