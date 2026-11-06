"""AeroCIE-030: interchange JSON/CSV source adapters without changing risk logic."""
from __future__ import annotations

import csv
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.aerocie.prime_adapters import (
    BUNDLE_SCHEMA, CSV_HEADERS, evaluate_source, load_csv_bundle, load_json,
)

FIXTURE = Path(__file__).resolve().parents[1] / "sample-data" / "prime_scrm_synthetic.json"


def write_bundle(folder: Path, payload: dict) -> None:
    """Produce a local test bundle from the existing fictional JSON fixture."""
    folder.mkdir(parents=True, exist_ok=True)
    files = {}
    for name, rows in (
        ("evidence.csv", payload["evidence"]),
        ("suppliers.csv", payload["suppliers"]),
        ("components.csv", payload["components"]),
    ):
        with (folder / name).open("w", encoding="utf-8", newline="") as target:
            writer = csv.DictWriter(target, fieldnames=CSV_HEADERS[name], lineterminator="\n")
            writer.writeheader()
            for row in rows:
                writer.writerow({k: (str(row[k]).lower() if isinstance(row[k], bool) else row[k])
                                 for k in CSV_HEADERS[name]})
        files[name] = hashlib.sha256((folder / name).read_bytes()).hexdigest()
    manifest = {
        "bundle_schema": BUNDLE_SCHEMA,
        "schema": payload["schema"],
        "program": payload["program"],
        "data_classification": payload["data_classification"],
        "external_release_authorized": payload["external_release_authorized"],
        "files": files,
    }
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.bundle = self.root / "bundle"
        write_bundle(self.bundle, self.payload)

    def _repin(self, name: str) -> None:
        path = self.bundle / "manifest.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        manifest["files"][name] = hashlib.sha256((self.bundle / name).read_bytes()).hexdigest()
        path.write_text(json.dumps(manifest), encoding="utf-8")

    def test_two_adapters_return_identical_research_output(self):
        self.assertEqual(load_json(FIXTURE), load_csv_bundle(self.bundle))
        json_result = evaluate_source("json", FIXTURE)
        csv_result = evaluate_source("csv", self.bundle)
        self.assertEqual(json_result, csv_result)
        self.assertFalse(json_result["external_release_authorized"])
        self.assertEqual(json_result["summary"]["review_flag_count"], 2)
        self.assertIn("NOT_AVAILABLE", json_result["summary"]["schedule_forecast"])

    def test_csv_tamper_blocks_before_scoring(self):
        target = self.bundle / "components.csv"
        target.write_bytes(target.read_bytes().replace(b"75", b"76"))
        with self.assertRaisesRegex(ValueError, "Integrity mismatch"):
            evaluate_source("csv", self.bundle)

    def test_missing_or_unlisted_files_block(self):
        (self.bundle / "suppliers.csv").unlink()
        with self.assertRaises(ValueError):
            load_csv_bundle(self.bundle)
        write_bundle(self.bundle, self.payload)
        manifest_file = self.bundle / "manifest.json"
        manifest = json.loads(manifest_file.read_text())
        manifest["files"]["outside.csv"] = "0" * 64
        manifest_file.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "allowlist"):
            load_csv_bundle(self.bundle)

    def test_invalid_csv_columns_block_even_with_updated_pin(self):
        target = self.bundle / "suppliers.csv"
        target.write_text("supplier_id,unexpected\nS001,Fictional\n", encoding="utf-8")
        self._repin("suppliers.csv")
        with self.assertRaisesRegex(ValueError, "column headers"):
            load_csv_bundle(self.bundle)

    def test_wrong_boolean_and_negative_lead_time_block(self):
        target = self.bundle / "components.csv"
        text = target.read_text(encoding="utf-8")
        target.write_text(text.replace("true", "maybe", 1), encoding="utf-8")
        self._repin("components.csv")
        with self.assertRaisesRegex(ValueError, "true or false"):
            load_csv_bundle(self.bundle)
        write_bundle(self.bundle, self.payload)
        text = target.read_text(encoding="utf-8")
        target.write_text(text.replace(",75,", ",-1,", 1), encoding="utf-8")
        self._repin("components.csv")
        with self.assertRaisesRegex(ValueError, "whole number"):
            load_csv_bundle(self.bundle)

    def test_metadata_cannot_bypass_synthetic_gate(self):
        manifest_file = self.bundle / "manifest.json"
        manifest = json.loads(manifest_file.read_text())
        manifest["data_classification"] = "CUI"
        manifest_file.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "synthetic"):
            evaluate_source("csv", self.bundle)

    def test_json_duplicate_keys_and_nonfinite_numbers_block(self):
        target = self.root / "duplicate.json"
        target.write_text('{"schema":"x","schema":"y"}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Duplicate JSON key"):
            load_json(target)
        target.write_text('{"schema":NaN}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Non-finite"):
            load_json(target)

    def test_symlink_and_oversize_block(self):
        oversized = self.root / "too-big.json"
        oversized.write_bytes(b" " * 1_000_001)
        with self.assertRaisesRegex(ValueError, "size limit"):
            load_json(oversized)
        try:
            link = self.root / "linked.json"
            link.symlink_to(FIXTURE)
        except (OSError, NotImplementedError):
            self.skipTest("Creating symlinks unsupported on this system")
        with self.assertRaisesRegex(ValueError, "non-symlink"):
            load_json(link)

    def test_unknown_adapter_rejected(self):
        with self.assertRaisesRegex(ValueError, "Adapter must be"):
            evaluate_source("remote", FIXTURE)


if __name__ == "__main__":
    unittest.main()
