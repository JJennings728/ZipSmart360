"""AeroCIE-014 offline self-attested review journal regression tests."""
from contextlib import closing, redirect_stdout
import io
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from src.aerocie import audit_packet
from src.aerocie import review_journal as journal


class ReviewJournalTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        self.packet = root / "unsigned-packet.json"
        self.db = root / "review-events.sqlite3"
        packet = {
            "packet_schema": "AEROCIE-013-UNSIGNED-RESEARCH-DRAFT-v1",
            "human_review_checklist": [
                {"check_id": key, "status": "PENDING_HUMAN_REVIEW"}
                for key, _ in audit_packet.CHECKS
            ],
            "external_release_authorized": False,
            "human_review_complete": False,
            "compliance_status": "NOT_DETERMINED",
            "review_disposition": "HOLD_FOR_HUMAN_REVIEW",
        }
        packet["audit_sha256"] = audit_packet._sha(packet)
        self.packet.write_text(json.dumps(packet), encoding="utf-8")
        self.args = dict(
            packet_path=self.packet, journal=self.db,
            check_id="source_text", status="CHECKED_RESEARCH_ONLY",
            reviewer="Synthetic Analyst", reviewer_role="Research QA",
            notes="Personally examined the synthetic test publication and recorded its scope.",
            citation="Synthetic Federal Register test citation, 91 FR 59987",
            attest=True,
        )

    def test_empty_journal_is_pending_and_no_file_written(self):
        result = journal.summary(self.packet, self.db)
        self.assertEqual(result["journal_event_count"], 0)
        self.assertFalse(self.db.exists())
        self.assertTrue(all(x == "PENDING_HUMAN_REVIEW"
                            for x in result["latest_checklist_states"].values()))

    def test_records_self_attested_step_without_approval(self):
        recorded = journal.record_check(**self.args)
        self.assertEqual(recorded["recorded_sequence"], 1)
        state = journal.summary(self.packet, self.db)
        self.assertEqual(state["journal_event_count"], 1)
        self.assertEqual(state["latest_checklist_states"]["source_text"],
                         "CHECKED_RESEARCH_ONLY")
        self.assertFalse(state["external_release_authorized"])
        self.assertFalse(state["human_review_complete"])
        self.assertFalse(state["events"][0]["identity_authenticated"])

    def test_explicit_attestation_required(self):
        with self.assertRaises(ValueError):
            journal.record_check(**{**self.args, "attest": False})
        self.assertFalse(self.db.exists())

    def test_source_citation_required_for_checked_step(self):
        with self.assertRaises(ValueError):
            journal.record_check(**{**self.args, "citation": ""})
        self.assertFalse(self.db.exists())

    def test_rejects_unsupported_compliance_approval(self):
        with self.assertRaises(ValueError):
            journal.record_check(**{**self.args, "status": "FAA_APPROVED"})

    def test_prevents_short_inadequate_research_notes(self):
        with self.assertRaises(ValueError):
            journal.record_check(**{**self.args, "notes": "done"})

    def test_followup_event_requires_notes_not_fabricated_citation(self):
        event = journal.record_check(
            **{**self.args, "status": "FOLLOW_UP_REQUIRED", "citation": ""})
        self.assertEqual(event["status"], "FOLLOW_UP_REQUIRED")
        self.assertEqual(journal.summary(self.packet, self.db)["journal_event_count"], 1)

    def test_append_only_event_history_with_latest_status(self):
        journal.record_check(**self.args)
        journal.record_check(**{
            **self.args, "status": "FOLLOW_UP_REQUIRED", "citation": "",
            "notes": "Found that official later amendments were not verified and require further analysis.",
        })
        summary = journal.summary(self.packet, self.db)
        self.assertEqual(summary["journal_event_count"], 2)
        self.assertEqual(summary["events"][1]["previous_event_sha256"],
                         journal._digest(summary["events"][0]))
        self.assertEqual(summary["latest_checklist_states"]["source_text"],
                         "FOLLOW_UP_REQUIRED")

    def test_event_update_and_delete_blocked(self):
        journal.record_check(**self.args)
        with closing(sqlite3.connect(self.db)) as conn:
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute("UPDATE review_events SET event_json='{}' WHERE seq=1")
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute("DELETE FROM review_events WHERE seq=1")

    def test_invalid_hash_chain_detected_even_without_trigger(self):
        journal.record_check(**self.args)
        with closing(sqlite3.connect(self.db)) as conn:
            conn.execute("DROP TRIGGER review_events_no_update")
            conn.execute("UPDATE review_events SET event_json='{}' WHERE seq=1")
            conn.commit()
        with self.assertRaises(ValueError):
            journal.summary(self.packet, self.db)

    def test_other_packet_cannot_reuse_the_journal(self):
        journal.record_check(**self.args)
        packet = json.loads(self.packet.read_text())
        packet["test_modified"] = True
        packet["audit_sha256"] = audit_packet._sha({
            key: value for key, value in packet.items() if key != "audit_sha256"})
        self.packet.write_text(json.dumps(packet))
        with self.assertRaises(ValueError):
            journal.summary(self.packet, self.db)

    def test_reject_nonreview_existing_sqlite_database(self):
        with closing(sqlite3.connect(self.db)) as conn:
            conn.execute("CREATE TABLE document_snapshots(id INTEGER)")
            conn.commit()
        with self.assertRaises(ValueError):
            journal.record_check(**self.args)

    def test_packet_checksum_tampering_refused(self):
        data = json.loads(self.packet.read_text())
        data["compliance_status"] = "APPROVED"
        self.packet.write_text(json.dumps(data))
        with self.assertRaises(ValueError):
            journal.record_check(**self.args)

    def test_all_checklist_entries_cannot_auto_authorize(self):
        for check_id, _ in audit_packet.CHECKS:
            journal.record_check(**{**self.args, "check_id": check_id})
        state = journal.summary(self.packet, self.db)
        self.assertEqual(state["journal_event_count"], 8)
        self.assertFalse(state["human_review_complete"])
        self.assertFalse(state["external_release_authorized"])
        self.assertEqual(state["applicability_status"], "NOT_DETERMINED")

    def test_cli_status_only_does_not_create_ledger(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = journal.main([
                "--packet", str(self.packet), "--journal", str(self.db),
                "status"])
        self.assertEqual(code, 0)
        self.assertIn('"external_release_authorized": false', buffer.getvalue())
        self.assertFalse(self.db.exists())

    def test_cli_records_self_attested_step(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = journal.main([
                "--packet", str(self.packet), "--journal", str(self.db),
                "record-check", "--check-id", "source_text",
                "--status", "CHECKED_RESEARCH_ONLY", "--reviewer",
                "Synthetic Analyst", "--reviewer-role", "Internal QA",
                "--notes", "I personally examined the synthetic test source citation and its listed text.",
                "--citation", "91 FR 59987 synthetic test document",
                "--attest"])
        self.assertEqual(code, 0)
        self.assertEqual(journal.summary(self.packet, self.db)["journal_event_count"], 1)


if __name__ == "__main__":
    unittest.main()
