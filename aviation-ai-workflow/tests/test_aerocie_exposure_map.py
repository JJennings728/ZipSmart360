"""AeroCIE-012 safety and provenance tests; synthetic/offline fixtures."""
from contextlib import closing, redirect_stdout
import io
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest

from src.aerocie import exposure_map as em
from src.aerocie import fr_collector, knowledge_graph as kg


class ExposureMappingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.source = root / "collector.sqlite3"
        self.graph = root / "graph.sqlite3"
        self.registry = root / "research-exposure.sqlite3"
        self.original = {
            "document_number": "2026-19391",
            "title": "Synthetic Airspace Rule",
            "type": "Rule", "publication_date": "2026-09-22",
            "effective_on": "2026-12-24",
            "action": "Final rule.",
            "abstract": "Synthetic restriction for a test facility.",
            "docket_ids": ["FAA-2026-8548"],
            "citation": "91 FR 59987",
            "html_url": "https://www.federalregister.gov/documents/test-original",
        }
        self.quote = ("This action corrects a final rule published by "
                      "the FAA on September 22, 2026.")
        self.correction = {
            **self.original,
            "document_number": "2026-21995",
            "title": "Synthetic Airspace Rule; Correction",
            "action": "Final rule; correction.",
            "publication_date": "2026-10-28",
            "abstract": self.quote,
            "citation": "91 FR 67769",
            "html_url": "https://www.federalregister.gov/documents/test-correction",
        }
        with closing(sqlite3.connect(self.source)) as conn:
            fr_collector.initialize(conn)
            fr_collector.ingest(conn, self.original, source="published")
            fr_collector.ingest(conn, self.correction, source="published")
        self.original_doc = kg.import_federal_register(
            self.graph, self.source, "2026-19391")
        self.correction_doc = kg.import_federal_register(
            self.graph, self.source, "2026-21995")
        kg.add_node(self.graph, node_id="frdoc:2026-19391",
                    kind="PUBLICATION", label="Original", source_db=self.source)
        kg.add_node(self.graph, node_id="frdoc:2026-21995",
                    kind="PUBLICATION", label="Correction", source_db=self.source)
        em.add_subject(
            self.registry, subject_id="demo:facility:1",
            subject_type="FACILITY", label="Synthetic Test Facility",
            source_db=self.source, graph_db=self.graph)

    def propose(self, **updates):
        opts = dict(
            db=self.registry, subject_id="demo:facility:1",
            document_number="2026-21995", excerpt=self.quote,
            rationale="Research whether this publication merits facility review.",
            locator="Synthetic published metadata abstract",
            researcher="SRP internal test", source_db=self.source,
            graph_db=self.graph)
        opts.update(updates)
        return em.propose(**opts)

    def latest(self):
        return em.export_candidates(
            self.registry, self.source, self.graph)["candidates"][0]

    def corrects(self):
        kg.add_edge(
            self.graph, from_id="frdoc:2026-21995",
            to_id="frdoc:2026-19391", predicate="CORRECTS",
            doc_id=self.correction_doc["id"], excerpt=self.quote,
            locator="Synthetic metadata abstract", actor="SRP synthetic",
            source_db=self.source)

    def test_proposal_is_not_applicability_determination(self):
        result = self.propose()
        self.assertEqual(result["research_state"], "PROPOSED_RESEARCH_ONLY")
        reg = em.export_candidates(self.registry, self.source, self.graph)
        self.assertEqual(len(reg["candidates"]), 1)
        candidate = reg["candidates"][0]
        self.assertEqual(candidate["evidence_status"],
                         "LOCAL_SOURCE_PIN_MATCH_ONLY_NOT_APPLICABILITY")
        self.assertEqual(candidate["applicability_status"], "NOT_DETERMINED")
        self.assertEqual(candidate["operational_exposure_status"], "NOT_DETERMINED")
        self.assertFalse(reg["external_release_authorized"])
        self.assertFalse(candidate["human_review_complete"])

    def test_subject_types_and_immutable_identity(self):
        again = em.add_subject(
            self.registry, subject_id="demo:facility:1",
            subject_type="FACILITY", label="Synthetic Test Facility",
            source_db=self.source, graph_db=self.graph)
        self.assertEqual(again["event"], "existing_same_subject")
        with self.assertRaises(ValueError):
            em.add_subject(
                self.registry, subject_id="demo:facility:1",
                subject_type="AIRCRAFT", label="Changed", source_db=self.source,
                graph_db=self.graph)
        with self.assertRaises(ValueError):
            em.add_subject(
                self.registry, subject_id="demo:space:1",
                subject_type="UNKNOWN", label="Unsupported", source_db=self.source,
                graph_db=self.graph)

    def test_unknown_subject_rejected(self):
        with self.assertRaises(ValueError):
            self.propose(subject_id="demo:unknown")

    def test_exact_excerpt_required_and_tampering_rejected(self):
        with self.assertRaises(ValueError):
            self.propose(excerpt="fabricated nonexistent FAA source excerpt")
        self.propose()
        with closing(sqlite3.connect(self.graph)) as conn:
            with conn:
                conn.execute("UPDATE kg_documents SET content='{}' WHERE id=?",
                             (self.correction_doc["id"],))
        self.assertEqual(self.latest()["evidence_status"],
                         "GRAPH_DOCUMENT_INTEGRITY_FAILURE")

    def test_newer_local_source_requires_review(self):
        self.propose()
        with closing(sqlite3.connect(self.source)) as conn:
            fr_collector.ingest(
                conn, {**self.correction, "title": "Revised metadata"},
                source="published")
        self.assertEqual(self.latest()["evidence_status"],
                         "NEWER_LOCAL_METADATA_REQUIRES_REVIEW")

    def test_new_source_version_cannot_be_linked_until_imported(self):
        with closing(sqlite3.connect(self.source)) as conn:
            fr_collector.ingest(
                conn, {**self.correction, "title": "New metadata version"},
                source="published")
        with self.assertRaises(ValueError):
            self.propose()

    def test_missing_pinned_collector_snapshot_requires_review(self):
        self.propose()
        with closing(sqlite3.connect(self.source)) as conn:
            with conn:
                conn.execute("DELETE FROM document_snapshots "
                             "WHERE document_number='2026-21995'")
        self.assertEqual(self.latest()["evidence_status"],
                         "PINNED_SOURCE_UNAVAILABLE_OR_INVALID")

    def test_missing_graph_publication_node_blocks_proposal(self):
        with closing(sqlite3.connect(self.graph)) as conn:
            with conn:
                conn.execute("DELETE FROM kg_nodes WHERE id='frdoc:2026-21995'")
        with self.assertRaises(ValueError):
            self.propose()

    def test_valid_correction_lineage_remains_research_only(self):
        self.corrects()
        self.propose()
        result = self.latest()
        self.assertEqual(result["related_local_correction_candidates"], 1)
        self.assertEqual(result["correction_evidence_statuses"], [em.PIN_OK])
        self.assertFalse(result["requires_review"])
        self.assertEqual(result["applicability_status"], "NOT_DETERMINED")

    def test_missing_original_pin_flags_correction_research(self):
        self.corrects()
        self.propose()
        with closing(sqlite3.connect(self.graph)) as conn:
            with conn:
                conn.execute("DELETE FROM kg_correction_pins")
        result = self.latest()
        self.assertEqual(result["correction_evidence_statuses"],
                         ["ORIGINAL_PIN_MISSING_REQUIRES_REVIEW"])
        self.assertTrue(result["requires_review"])

    def test_source_and_graph_database_write_guards(self):
        with self.assertRaises(ValueError):
            em.initialize(self.source, self.source, self.graph)
        with self.assertRaises(ValueError):
            em.initialize(self.graph, self.source, self.graph)
        with self.assertRaises(ValueError):
            em.initialize(self.source, self.registry, self.graph)

    def test_duplicate_proposal_is_blocked(self):
        self.propose()
        with self.assertRaises(sqlite3.IntegrityError):
            self.propose()

    def test_no_customer_data_or_external_calls_in_cli(self):
        out = io.StringIO()
        with redirect_stdout(out):
            status = em.main([
                "--db", str(self.registry), "--source-db", str(self.source),
                "--graph-db", str(self.graph), "export"])
        self.assertEqual(status, 0)
        self.assertIn('"external_release_authorized": false', out.getvalue())
        self.assertNotIn('"applicability_status": "APPLICABLE"', out.getvalue())


if __name__ == "__main__":
    unittest.main()
