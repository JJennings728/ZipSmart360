"""AeroCIE-031 | fail-closed synthetic reconciliation and packet tests."""
from __future__ import annotations

import csv
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from src.aerocie.prime_adapters import BUNDLE_SCHEMA, CSV_HEADERS
from src.aerocie.prime_pilot import digest, evaluate
from src.aerocie import prime_reconciliation as reconcile

FIXTURE = Path(__file__).resolve().parents[1] / "sample-data" / "prime_scrm_synthetic.json"


def write_bundle(folder: Path, payload: dict) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for file_name, kind in (("evidence.csv", "evidence"),
                            ("suppliers.csv", "suppliers"),
                            ("components.csv", "components")):
        with (folder / file_name).open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=CSV_HEADERS[file_name], lineterminator="\n")
            writer.writeheader()
            for row in payload[kind]:
                writer.writerow({k: str(row[k]).lower() if type(row[k]) is bool else row[k]
                                 for k in CSV_HEADERS[file_name]})
        hashes[file_name] = hashlib.sha256((folder / file_name).read_bytes()).hexdigest()
    manifest = {
        "bundle_schema": BUNDLE_SCHEMA,
        "schema": payload["schema"],
        "program": payload["program"],
        "data_classification": payload["data_classification"],
        "external_release_authorized": payload["external_release_authorized"],
        "files": hashes,
    }
    (folder / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8")


class PrimeReconciliationTests(unittest.TestCase):
    def setUp(self):
        context = TemporaryDirectory()
        self.addCleanup(context.cleanup)
        self.root = Path(context.name)
        self.payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.baseline = self.root / "baseline.json"
        self.baseline.write_text(json.dumps(self.payload), encoding="utf-8")

    def write_payload(self, payload: dict, name: str = "changed.json") -> Path:
        target = self.root / name
        target.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return target

    def test_packet_has_reconciled_totals_traceability_and_no_release(self):
        packet = reconcile.build_packet("json", FIXTURE)
        self.assertEqual(packet["source_counts"], {
            "evidence": 3, "suppliers": 3, "components": 3})
        self.assertEqual(packet["model_summary"]["review_flag_count"], 2)
        self.assertEqual(packet["model_summary"]["single_source_assumptions"], 2)
        self.assertEqual(len(packet["open_review_items"]), 2)
        self.assertEqual(packet["reviewer_disposition"], "NOT_RECORDED")
        self.assertFalse(packet["release_authorized"])
        self.assertEqual(packet["packet_sha256"], digest({
            key: value for key, value in packet.items() if key != "packet_sha256"}))
        for item in packet["open_review_items"]:
            self.assertRegex(item["evidence_sha256"], r"^[a-f0-9]{64}$")
            self.assertIn(item["component_id"], packet["source_record_sha256"]["components"])
            self.assertEqual(item["human_disposition"], "OPEN_NOT_REVIEWED")

    def test_same_input_repeat_is_deterministic(self):
        self.assertEqual(reconcile.build_packet("json", FIXTURE),
                         reconcile.build_packet("json", FIXTURE))

    def test_json_csv_reconcile_same_model_and_record_fingerprints(self):
        bundle = self.root / "bundle"
        write_bundle(bundle, self.payload)
        a = reconcile.build_packet("json", FIXTURE)
        b = reconcile.build_packet("csv", bundle)
        self.assertEqual(a["source_input_sha256"], b["source_input_sha256"])
        self.assertEqual(a["model_report_sha256"], b["model_report_sha256"])
        self.assertEqual(a["source_record_sha256"], b["source_record_sha256"])
        self.assertEqual(a["open_review_items"], b["open_review_items"])
        self.assertNotEqual(a["packet_sha256"], b["packet_sha256"])  # adapter provenance differs

    def test_snapshot_diff_detects_added_removed_modified(self):
        changed = deepcopy(self.payload)
        changed["components"] = [
            row for row in changed["components"] if row["component_id"] != "C002"
        ]
        changed["components"][0]["scenario_lead_days"] = 80
        added = deepcopy(changed["components"][0])
        added.update(component_id="C004", supplier_id="S003", evidence_id="E003")
        changed["components"].append(added)
        latest = self.write_payload(changed)
        packet = reconcile.build_packet(
            "json", latest, baseline_adapter="json", baseline_source=self.baseline)
        delta = packet["source_changes_since_baseline"]["components"]
        self.assertEqual(delta["added_ids"], ["C004"])
        self.assertEqual(delta["removed_ids"], ["C002"])
        self.assertEqual(delta["modified_ids"], ["C001"])
        self.assertTrue(packet["source_changes_since_baseline"]["changed"])
        self.assertEqual(packet["baseline_input_sha256"], digest(self.payload))

    def test_modified_pinned_evidence_shown_as_changed(self):
        changed = deepcopy(self.payload)
        changed["evidence"][0]["text"] += " Additional synthetic note."
        changed["evidence"][0]["sha256"] = hashlib.sha256(
            changed["evidence"][0]["text"].encode("utf-8")).hexdigest()
        latest = self.write_payload(changed)
        packet = reconcile.build_packet(
            "json", latest, baseline_adapter="json", baseline_source=self.baseline)
        self.assertEqual(
            packet["source_changes_since_baseline"]["evidence"]["modified_ids"],
            ["E001"])

    def test_cross_program_baseline_is_refused(self):
        changed = deepcopy(self.payload)
        changed["program"] = "Another fictional program"
        latest = self.write_payload(changed)
        with self.assertRaisesRegex(ValueError, "different program"):
            reconcile.build_packet(
                "json", latest, baseline_adapter="json",
                baseline_source=self.baseline)

    def test_baseline_arguments_must_be_complete(self):
        with self.assertRaisesRegex(ValueError, "provided together"):
            reconcile.build_packet("json", FIXTURE, baseline_adapter="json")
        with self.assertRaisesRegex(ValueError, "provided together"):
            reconcile.build_packet("json", FIXTURE, baseline_source=self.baseline)

    def test_cui_or_release_flag_fails_closed(self):
        for key, value in (("data_classification", "CUI"),
                           ("data_classification", "FCI"),
                           ("external_release_authorized", True)):
            changed = deepcopy(self.payload)
            changed[key] = value
            latest = self.write_payload(changed)
            with self.assertRaises(ValueError):
                reconcile.build_packet("json", latest)

    def test_evidence_tamper_and_missing_reference_fail_closed(self):
        changed = deepcopy(self.payload)
        changed["evidence"][0]["text"] += " changed"
        with self.assertRaisesRegex(ValueError, "fingerprint mismatch"):
            reconcile.build_packet("json", self.write_payload(changed))
        changed = deepcopy(self.payload)
        changed["components"][0]["evidence_id"] = "UNKNOWN"
        with self.assertRaisesRegex(ValueError, "Unresolved"):
            reconcile.build_packet("json", self.write_payload(changed))

    def test_model_summary_mismatch_is_independently_blocked(self):
        forged = evaluate(self.payload)
        forged["summary"]["supplier_count"] += 7
        forged["report_sha256"] = digest({
            k: v for k, v in forged.items() if k != "report_sha256"})
        with patch.object(reconcile, "evaluate", return_value=forged):
            with self.assertRaisesRegex(ValueError, "summary"):
                reconcile.build_packet("json", FIXTURE)

    def test_invented_forecast_is_refused_even_with_updated_digest(self):
        forged = evaluate(self.payload)
        forged["summary"]["schedule_forecast"] = 30
        forged["report_sha256"] = digest({
            k: v for k, v in forged.items() if k != "report_sha256"})
        with patch.object(reconcile, "evaluate", return_value=forged):
            with self.assertRaisesRegex(ValueError, "forecast"):
                reconcile.build_packet("json", FIXTURE)

    def test_unreferenced_metadata_is_review_question_not_false_clearance(self):
        changed = deepcopy(self.payload)
        changed["suppliers"].append({"supplier_id": "S004", "name": "Fictional Unused"})
        changed["evidence"].append({
            "evidence_id": "E004",
            "text": "Synthetic, unused supplier note.",
            "sha256": hashlib.sha256(b"Synthetic, unused supplier note.").hexdigest(),
            "synthetic": True})
        packet = reconcile.build_packet("json", self.write_payload(changed))
        codes = {item["code"] for item in packet["data_quality_findings"]}
        self.assertEqual(codes, {"UNREFERENCED_SUPPLIER", "UNREFERENCED_EVIDENCE"})

    def test_markdown_escapes_program_and_detects_packet_tampering(self):
        payload = deepcopy(self.payload)
        payload["program"] = "Fictional | <script> research"
        packet = reconcile.build_packet("json", self.write_payload(payload))
        text = reconcile.render_markdown(packet)
        self.assertIn("&#124;", text)
        self.assertIn("&lt;script&gt;", text)
        self.assertNotIn("<script>", text)
        self.assertIn("HUMAN", packet["decision_status"])
        forged = deepcopy(packet)
        forged["open_review_items"][0]["lead_time_increase_days"] = 999
        with self.assertRaisesRegex(ValueError, "fingerprint mismatch"):
            reconcile.render_markdown(forged)

    def test_cli_writes_two_files_without_overwrite(self):
        json_out = self.root / "packet.json"
        md_out = self.root / "packet.md"
        args = ["--adapter", "json", "--source", str(FIXTURE),
                "--output-json", str(json_out), "--output-md", str(md_out)]
        self.assertEqual(reconcile.main(args), 0)
        self.assertEqual(json.loads(json_out.read_text())["schema"],
                         reconcile.PACKET_SCHEMA)
        self.assertIn("Human review queue", md_out.read_text())
        with self.assertRaises(SystemExit) as context:
            reconcile.main(args)
        self.assertEqual(context.exception.code, 2)

    def test_csv_fingerprint_tamper_fails(self):
        bundle = self.root / "bundle"
        write_bundle(bundle, self.payload)
        target = bundle / "components.csv"
        target.write_bytes(target.read_bytes().replace(b"75", b"76"))
        with self.assertRaisesRegex(ValueError, "Integrity mismatch"):
            reconcile.build_packet("csv", bundle)


if __name__ == "__main__":
    unittest.main()
