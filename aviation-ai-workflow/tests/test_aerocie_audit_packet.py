"""AeroCIE-013 offline evidence-review tests using synthetic sources."""
from contextlib import closing, redirect_stdout
import io
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from src.aerocie import audit_packet as audit
from src.aerocie import fr_collector as fr, knowledge_graph as kg, exposure_map as em


class AuditPacketTests(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        self.source = root / "collector.sqlite3"
        self.graph = root / "graph.sqlite3"
        self.registry = root / "exposure.sqlite3"
        self.reviews = root / "reviews"
        self.json_path = root / "packet.json"
        self.html_path = root / "packet.html"
        original = {
            "document_number": "2026-19391", "title": "Synthetic original",
            "type": "Rule", "publication_date": "2026-09-22",
            "effective_on": "2026-12-24", "action": "Final rule.",
            "abstract": "Research fixture only.",
            "docket_ids": ["FAA-2026-8548"], "citation": "91 FR 59987",
            "html_url": "https://www.federalregister.gov/documents/test-original",
        }
        self.quote = ("This action corrects a final rule published by "
                      "the FAA on September 22, 2026.")
        self.correction = {
            **original, "document_number": "2026-21995",
            "title": "Synthetic correction", "publication_date": "2026-10-28",
            "action": "Final rule; correction.",
            "abstract": self.quote, "citation": "91 FR 67769",
            "html_url": "https://www.federalregister.gov/documents/test-correction",
        }
        with closing(sqlite3.connect(self.source)) as conn:
            fr.initialize(conn)
            fr.ingest(conn, original, source="published")
            fr.ingest(conn, self.correction, source="published")
        kg.import_federal_register(self.graph, self.source, "2026-19391")
        correction = kg.import_federal_register(
            self.graph, self.source, "2026-21995")
        self.graph_doc = correction["id"]
        kg.add_node(self.graph, node_id="frdoc:2026-19391",
                    kind="PUBLICATION", label="Original", source_db=self.source)
        kg.add_node(self.graph, node_id="frdoc:2026-21995",
                    kind="PUBLICATION", label="Correction", source_db=self.source)
        kg.add_edge(
            self.graph, from_id="frdoc:2026-21995",
            to_id="frdoc:2026-19391", predicate="CORRECTS",
            doc_id=correction["id"], excerpt=self.quote,
            locator="Synthetic abstract", actor="QA",
            source_db=self.source)
        em.add_subject(
            self.registry, subject_id="demo:facility:17",
            subject_type="FACILITY", label="Synthetic Facility",
            source_db=self.source, graph_db=self.graph)
        self.candidate_id = em.propose(
            self.registry, subject_id="demo:facility:17",
            document_number="2026-21995", excerpt=self.quote,
            rationale="Verify whether this correction warrants further research.",
            locator="Synthetic abstract", researcher="QA",
            source_db=self.source, graph_db=self.graph)["candidate_id"]

    def packet(self, **kw):
        args = dict(
            registry_db=self.registry, source_db=self.source,
            graph_db=self.graph, candidate_id=self.candidate_id,
            as_of="2026-10-28", reviews_dir=self.reviews)
        args.update(kw)
        return audit.build_packet(**args)

    def test_source_timeline_and_correction_lineage_included(self):
        p = self.packet()
        self.assertTrue(audit.verify_packet_hash(p))
        self.assertEqual(len(p["published_metadata_documents"]), 2)
        self.assertEqual(len(p["timeline_events_metadata_only"]), 4)
        self.assertEqual(len(p["correction_candidates_research_only"]), 1)
        self.assertFalse(p["source_integrity_or_refresh_review_needed"])

    def test_no_automatic_authorization(self):
        p = self.packet()
        self.assertEqual(p["review_disposition"], "HOLD_FOR_HUMAN_REVIEW")
        self.assertEqual(p["applicability_status"], "NOT_DETERMINED")
        self.assertEqual(p["compliance_status"], "NOT_DETERMINED")
        self.assertFalse(p["external_release_authorized"])
        self.assertFalse(p["human_review_complete"])
        self.assertIsNone(p["reviewer_name"])
        self.assertEqual(len(p["human_review_checklist"]), 8)

    def test_original_pin_missing_is_flagged(self):
        with closing(sqlite3.connect(self.graph)) as conn:
            with conn:
                conn.execute("DELETE FROM kg_correction_pins")
        p = self.packet()
        self.assertTrue(p["source_integrity_or_refresh_review_needed"])
        self.assertEqual(
            p["correction_candidates_research_only"][0]["evidence_status"],
            "ORIGINAL_PIN_MISSING_REQUIRES_REVIEW")

    def test_updated_collector_requires_research_review(self):
        with closing(sqlite3.connect(self.source)) as conn:
            fr.ingest(conn, {**self.correction, "title": "Updated metadata"},
                      source="published")
        p = self.packet()
        self.assertTrue(p["source_integrity_or_refresh_review_needed"])
        self.assertEqual(p["research_candidate"]["evidence_status"],
                         "NEWER_LOCAL_METADATA_REQUIRES_REVIEW")

    def test_tampered_graph_evidence_requires_review(self):
        with closing(sqlite3.connect(self.graph)) as conn:
            with conn:
                conn.execute("UPDATE kg_documents SET content='{}' WHERE id=?",
                             (self.graph_doc,))
        p = self.packet()
        self.assertTrue(p["source_integrity_or_refresh_review_needed"])
        self.assertEqual(p["research_candidate"]["evidence_status"],
                         "GRAPH_DOCUMENT_INTEGRITY_FAILURE")

    def test_self_attested_source_receipt_not_approval(self):
        from src.aerocie.reviewer_packet import record_review
        record_review(
            self.source, self.reviews, document_number="2026-21995",
            reviewer="Synthetic analyst", reviewer_role="Internal QA",
            notes="Reviewed synthetic fixture and the metadata sources for testing.",
            disposition="source_reviewed_research_only",
            federal_register_checked=True, faa_drs_checked=True,
            supersession_checked=True)
        p = self.packet()
        record = next(d for d in p["published_metadata_documents"]
                      if d["document_number"] == "2026-21995")
        self.assertEqual(
            record["local_self_attested_source_review"]["state"],
            "source_reviewed_research_only")
        self.assertFalse(p["human_review_complete"])

    def test_html_escapes_untrusted_rationale(self):
        p = self.packet()
        p["research_candidate"]["rationale"] = '<img src=x onerror=alert(1)>'
        p["audit_sha256"] = audit._sha(
            {k: v for k, v in p.items() if k != "audit_sha256"})
        rendered = audit.render_html(p)
        self.assertIn("&lt;img", rendered)
        self.assertNotIn("<img", rendered)

    def test_audit_hash_detects_modification(self):
        p = self.packet()
        p["compliance_status"] = "AUTHORIZED"
        self.assertFalse(audit.verify_packet_hash(p))
        with self.assertRaises(ValueError):
            audit.render_html(p)

    def test_exclusive_write_and_no_overwrite(self):
        p = self.packet()
        dbs = (self.registry, self.source, self.graph)
        audit.write_packet(p, self.json_path, self.html_path,
                           evidence_databases=dbs)
        self.assertTrue(audit.verify_packet_hash(
            json.loads(self.json_path.read_text(encoding="utf-8"))))
        with self.assertRaises(FileExistsError):
            audit.write_packet(p, self.json_path, self.html_path,
                               evidence_databases=dbs)

    def test_refuses_output_overwriting_collector(self):
        p = self.packet()
        with self.assertRaises(ValueError):
            audit.write_packet(p, self.source, self.html_path,
                               evidence_databases=(self.registry, self.source, self.graph))

    def test_reject_invalid_candidate_and_date(self):
        with self.assertRaises(ValueError):
            self.packet(candidate_id=999)
        with self.assertRaises(ValueError):
            self.packet(as_of="2026-02-30")

    def test_input_dbs_not_modified(self):
        with closing(sqlite3.connect(self.source)) as conn:
            before = conn.execute("SELECT COUNT(*) FROM document_snapshots").fetchone()[0]
        self.packet()
        with closing(sqlite3.connect(self.source)) as conn:
            after = conn.execute("SELECT COUNT(*) FROM document_snapshots").fetchone()[0]
        self.assertEqual(before, after)

    def test_cli_produces_unsigned_json_and_html(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = audit.main([
                "--registry-db", str(self.registry),
                "--source-db", str(self.source),
                "--graph-db", str(self.graph),
                "--candidate-id", str(self.candidate_id),
                "--reviews-dir", str(self.reviews),
                "--as-of", "2026-10-28",
                "--out-json", str(self.json_path),
                "--out-html", str(self.html_path)])
        self.assertEqual(code, 0)
        self.assertIn('"external_release_authorized": false', buf.getvalue())
        self.assertIn("PENDING_HUMAN_REVIEW", self.html_path.read_text())


if __name__ == "__main__":
    unittest.main()
