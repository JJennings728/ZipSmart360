"""AeroCIE-033 | synthetic-only controlled internal export tests."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import zipfile

from src.aerocie.prime_reconciliation import build_packet
from src.aerocie.review_decision_ledger import initialize, record
from src.aerocie.prime_internal_export import create_internal_export, EXPORT_SCHEMA, main

FIXTURE = Path(__file__).resolve().parents[1] / "sample-data" / "prime_scrm_synthetic.json"
KEY = b"\x92" * 32
OTHER_KEY = b"\x71" * 32


class ExportGateTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.packet = build_packet("json", FIXTURE)
        self.db = self.root / "synthetic-journal.sqlite3"
        self.out = self.root / "synthetic-demo.zip"
        initialize(self.db, self.packet)

    def _decision(self, component_id, decision="RESEARCH_ACKNOWLEDGED"):
        return record(
            self.db, component_id=component_id, reviewer_id="SYNTHETIC_REVIEWER",
            decision=decision, reason="Synthetic research example with no release authority.",
            key_id="SYNTHETIC_TESTKEY", key=KEY,
        )

    def _ready(self):
        self._decision("C001")
        return self._decision("C003")["journal_head_sha256"]

    def test_no_reviews_blocks(self):
        with self.assertRaisesRegex(ValueError, "At least one anchored review"):
            create_internal_export(self.db, self.out, key=KEY, expected_head="0" * 64)
        self.assertFalse(self.out.exists())

    def test_missing_one_review_blocks(self):
        head = self._decision("C001")["journal_head_sha256"]
        with self.assertRaisesRegex(ValueError, "no recorded decision"):
            create_internal_export(self.db, self.out, key=KEY, expected_head=head)
        self.assertFalse(self.out.exists())

    def test_unresolved_final_disposition_blocks(self):
        self._ready()
        head = self._decision("C003", decision="MORE_EVIDENCE_REQUIRED")["journal_head_sha256"]
        with self.assertRaisesRegex(ValueError, "not acknowledged"):
            create_internal_export(self.db, self.out, key=KEY, expected_head=head)
        self.assertFalse(self.out.exists())

    def test_valid_export_has_only_three_fixed_files(self):
        head = self._ready()
        status = create_internal_export(self.db, self.out, key=KEY, expected_head=head)
        self.assertEqual(status["schema"], EXPORT_SCHEMA)
        self.assertEqual(status["acknowledged_components"], 2)
        self.assertFalse(status["external_release_authorized"])
        with zipfile.ZipFile(self.out) as archive:
            self.assertEqual(sorted(archive.namelist()), [
                "READ_ME_FIRST.txt", "internal_research_report.json", "manifest.json"
            ])
            notice = archive.read("READ_ME_FIRST.txt").decode()
            self.assertIn("NOT FOR CUSTOMER DELIVERY", notice)
            data = json.loads(archive.read("internal_research_report.json"))
            manifest = json.loads(archive.read("manifest.json"))
            self.assertEqual(data["head_sha256"], head)
            self.assertEqual(data["classification"], "PUBLIC_SYNTHETIC_ONLY")
            self.assertFalse(data["release_authorized"])
            self.assertEqual(len(data["research_acknowledgements"]), 2)
            for path, recorded in manifest["files_sha256"].items():
                self.assertEqual(hashlib.sha256(archive.read(path)).hexdigest(), recorded)

    def test_archive_reproducible_when_journal_unchanged(self):
        head = self._ready()
        first = create_internal_export(self.db, self.out, key=KEY, expected_head=head)
        second_out = self.root / "second.zip"
        second = create_internal_export(self.db, second_out, key=KEY, expected_head=head)
        self.assertEqual(first["package_sha256"], second["package_sha256"])
        self.assertEqual(self.out.read_bytes(), second_out.read_bytes())

    def test_existing_output_preserved(self):
        head = self._ready()
        self.out.write_bytes(b"existing important data")
        with self.assertRaises(FileExistsError):
            create_internal_export(self.db, self.out, key=KEY, expected_head=head)
        self.assertEqual(self.out.read_bytes(), b"existing important data")

    def test_wrong_secret_and_head_refused(self):
        head = self._ready()
        with self.assertRaisesRegex(ValueError, "HMAC"):
            create_internal_export(self.db, self.out, key=OTHER_KEY, expected_head=head)
        with self.assertRaisesRegex(ValueError, "External head anchor"):
            create_internal_export(self.db, self.out, key=KEY, expected_head="f" * 64)
        self.assertFalse(self.out.exists())

    def test_bad_output_suffix_and_missing_anchor(self):
        head = self._ready()
        with self.assertRaisesRegex(ValueError, "required"):
            create_internal_export(self.db, self.out, key=KEY, expected_head="")
        with self.assertRaisesRegex(ValueError, "must use .zip"):
            create_internal_export(self.db, self.root / "report.html", key=KEY, expected_head=head)

    def test_truncated_journal_fails_against_retained_anchor(self):
        head = self._ready()
        with sqlite3.connect(self.db) as con:
            con.execute("DROP TRIGGER block_event_delete")
            con.execute("DELETE FROM review_events WHERE seq=2")
        with self.assertRaisesRegex(ValueError, "External head anchor"):
            create_internal_export(self.db, self.out, key=KEY, expected_head=head)

    def test_export_carries_no_raw_evidence_excerpt(self):
        head = self._ready()
        create_internal_export(self.db, self.out, key=KEY, expected_head=head)
        with zipfile.ZipFile(self.out) as archive:
            report = archive.read("internal_research_report.json").decode()
        self.assertNotIn("Synthetic supplier interview", report)
        self.assertNotIn("Synthetic sourcing hypothetical", report)
        self.assertIn("NOT FOR CUSTOMER DELIVERY", report)

    def test_cli_requires_key_from_environment(self):
        head = self._ready()
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(SystemExit) as result:
                main(["--db", str(self.db), "--out", str(self.out),
                      "--expected-head", head])
        self.assertEqual(result.exception.code, 2)
        self.assertFalse(self.out.exists())

    def test_cli_success_with_test_key(self):
        head = self._ready()
        with patch.dict("os.environ", {"SRP_REVIEW_HMAC_KEY_HEX": KEY.hex()}):
            self.assertEqual(main(["--db", str(self.db), "--out", str(self.out),
                                   "--expected-head", head]), 0)
        self.assertTrue(zipfile.is_zipfile(self.out))


if __name__ == "__main__":
    unittest.main()
