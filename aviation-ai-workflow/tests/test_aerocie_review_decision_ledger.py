"""AeroCIE-032 | offline synthetic research decision journal tests."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from src.aerocie.prime_reconciliation import build_packet
from src.aerocie.review_decision_ledger import (
    DECISIONS, GENESIS, JOURNAL_SCHEMA, initialize, record, verify, main,
)

FIXTURE = Path(__file__).resolve().parents[1] / "sample-data" / "prime_scrm_synthetic.json"
TEST_KEY = bytes.fromhex("a3" * 32)
WRONG_KEY = bytes.fromhex("b4" * 32)


class DecisionLedgerTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.packet = build_packet("json", FIXTURE)
        self.db = self.root / "synthetic-review.sqlite3"

    def _initialize(self):
        return initialize(self.db, self.packet)

    def _record(self, *, component_id="C001",
                decision="MORE_EVIDENCE_REQUIRED",
                reason="Synthetic evidence needs another independent check.",
                key=TEST_KEY):
        return record(
            self.db, component_id=component_id, reviewer_id="REVIEWER_01",
            decision=decision, reason=reason, key_id="TESTKEY_01", key=key,
        )

    def test_create_new_journal_reject_existing_db(self):
        self.assertEqual(self._initialize(), self.packet["packet_sha256"])
        self.assertEqual(verify(self.db, TEST_KEY)["head_sha256"], GENESIS)
        with self.assertRaises(FileExistsError):
            self._initialize()

    def test_sequence_hmac_and_external_head_anchor(self):
        self._initialize()
        a = self._record()
        b = self._record(component_id="C003", decision="RESEARCH_ACKNOWLEDGED",
                         reason="Synthetic scenario reviewed for internal research only.")
        status = verify(self.db, TEST_KEY, expected_tip=b["journal_head_sha256"])
        self.assertEqual(status["event_count"], 2)
        self.assertTrue(status["externally_anchored"])
        self.assertFalse(status["external_release_authorized"])
        self.assertEqual(status["events"][1]["event"]["previous_sha256"],
                         a["journal_head_sha256"])
        self.assertEqual(status["events"][1]["event"]["component_id"], "C003")

    def test_wrong_signing_key_rejected(self):
        self._initialize()
        self._record()
        with self.assertRaisesRegex(ValueError, "HMAC"):
            verify(self.db, WRONG_KEY)

    def test_database_update_delete_triggers_block(self):
        self._initialize()
        self._record()
        with sqlite3.connect(self.db) as con:
            with self.assertRaises(sqlite3.IntegrityError):
                con.execute("DELETE FROM review_events WHERE seq=1")
            with self.assertRaises(sqlite3.IntegrityError):
                con.execute("UPDATE review_events SET event_sha256=? WHERE seq=1",
                            ("0" * 64,))

    def test_corrupt_hmac_detected_even_if_trigger_removed(self):
        self._initialize()
        self._record()
        with sqlite3.connect(self.db) as con:
            con.execute("DROP TRIGGER block_event_update")
            con.execute("UPDATE review_events SET hmac_sha256=? WHERE seq=1", ("f" * 64,))
        with self.assertRaisesRegex(ValueError, "HMAC"):
            verify(self.db, TEST_KEY)

    def test_truncated_history_detected_with_external_anchor(self):
        self._initialize()
        self._record()
        last = self._record(component_id="C003")
        with sqlite3.connect(self.db) as con:
            con.execute("DROP TRIGGER block_event_delete")
            con.execute("DELETE FROM review_events WHERE seq=2")
        self.assertEqual(verify(self.db, TEST_KEY)["event_count"], 1)
        with self.assertRaisesRegex(ValueError, "External head anchor"):
            verify(self.db, TEST_KEY, expected_tip=last["journal_head_sha256"])

    def test_unknown_component_and_missing_reason_rejected(self):
        self._initialize()
        with self.assertRaisesRegex(ValueError, "not in the research review queue"):
            self._record(component_id="C002")
        with self.assertRaisesRegex(ValueError, "Invalid reviewer"):
            self._record(reason="short")
        self.assertEqual(verify(self.db, TEST_KEY)["event_count"], 0)

    def test_weak_key_and_unsupported_decision_rejected(self):
        self._initialize()
        with self.assertRaisesRegex(ValueError, "Invalid reviewer"):
            self._record(key=b"short")
        with self.assertRaisesRegex(ValueError, "Invalid reviewer"):
            self._record(decision="APPROVE_EXTERNAL_RELEASE")
        self.assertEqual(verify(self.db, TEST_KEY)["event_count"], 0)

    def test_no_public_or_sensitive_data_accepted(self):
        for field, value in (("classification", "CUI"),
                             ("classification", "FCI"),
                             ("release_authorized", True),
                             ("decision_status", "APPROVED")):
            candidate = deepcopy(self.packet)
            candidate[field] = value
            db = self.root / ("candidate-" + field + ".sqlite3")
            with self.assertRaises(ValueError):
                initialize(db, candidate)
            self.assertFalse(db.exists())

    def test_packet_fingerprint_tamper_is_blocked(self):
        payload = deepcopy(self.packet)
        payload["program"] = "Modified after signing"
        with self.assertRaisesRegex(ValueError, "fingerprint invalid"):
            initialize(self.db, payload)

    def test_self_declared_actor_recorded_not_certified(self):
        self._initialize()
        self._record()
        event = verify(self.db, TEST_KEY)["events"][0]["event"]
        self.assertEqual(event["reviewer_id"], "REVIEWER_01")
        self.assertEqual(event["key_id"], "TESTKEY_01")
        self.assertNotIn("identity_verified", event)
        self.assertEqual(event["decision"], "MORE_EVIDENCE_REQUIRED")

    def test_event_body_tamper_rejected_with_trigger_removed(self):
        self._initialize()
        self._record()
        with sqlite3.connect(self.db) as con:
            row = json.loads(con.execute(
                "SELECT event_json FROM review_events WHERE seq=1").fetchone()[0])
            row["decision"] = "RESEARCH_ACKNOWLEDGED"
            con.execute("DROP TRIGGER block_event_update")
            con.execute("UPDATE review_events SET event_json=? WHERE seq=1",
                        (json.dumps(row, sort_keys=True, separators=(",", ":")),))
        with self.assertRaisesRegex(ValueError, "HMAC"):
            verify(self.db, TEST_KEY)

    def test_init_cli_and_verify_cli(self):
        packet_file = self.root / "packet.json"
        packet_file.write_text(json.dumps(self.packet), encoding="utf-8")
        self.assertEqual(main(["init", "--db", str(self.db), "--packet", str(packet_file)]), 0)
        with patch.dict("os.environ", {"SRP_REVIEW_HMAC_KEY_HEX": TEST_KEY.hex()}):
            self.assertEqual(main(["verify", "--db", str(self.db),
                                   "--expected-head", GENESIS]), 0)

    def test_missing_environment_secret_is_not_defaulted(self):
        self._initialize()
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(SystemExit) as err:
                main(["verify", "--db", str(self.db)])
        self.assertEqual(err.exception.code, 2)

    def test_packet_targets_remain_unreviewed_without_external_release(self):
        self._initialize()
        self._record(decision="RESEARCH_ACKNOWLEDGED",
                     reason="This is only an internal synthetic research acknowledgement.")
        status = verify(self.db, TEST_KEY)
        self.assertEqual(status["schema"], JOURNAL_SCHEMA)
        self.assertFalse(status["external_release_authorized"])
        self.assertIn("NOT_AUTHENTICATED_IDENTITY", status["verification"])


if __name__ == "__main__":
    unittest.main()
