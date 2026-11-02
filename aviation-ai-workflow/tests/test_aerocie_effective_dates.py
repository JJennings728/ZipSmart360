"""AeroCIE-011 offline metadata-timeline tests with synthetic collector data."""
from contextlib import closing, redirect_stdout
import io
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest

from src.aerocie import effective_dates as dates
from src.aerocie import fr_collector
from src.aerocie import knowledge_graph as kg


class EffectiveDateTimelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.source_db = root / "fr.sqlite3"
        self.graph_db = root / "graph.sqlite3"
        self.original = {
            "document_number": "2026-19391",
            "title": "Synthetic FAA Rule",
            "type": "Rule", "publication_date": "2026-09-22",
            "effective_on": "2026-12-24",
            "action": "Final rule.", "abstract": "Synthetic rule for tests.",
            "docket_ids": ["FAA-2026-8548"], "citation": "91 FR 59987",
            "html_url": "https://www.federalregister.gov/documents/example-original",
        }
        self.quote = ("This action corrects a final rule published by "
                      "the FAA on September 22, 2026.")
        self.correction = {
            **self.original, "document_number": "2026-21995",
            "title": "Synthetic FAA Rule; Correction",
            "publication_date": "2026-10-28",
            "action": "Final rule; correction.",
            "abstract": self.quote, "citation": "91 FR 67769",
            "html_url": "https://www.federalregister.gov/documents/example-correction",
        }
        with closing(sqlite3.connect(self.source_db)) as conn:
            fr_collector.initialize(conn)
            fr_collector.ingest(conn, self.original, source="published")
            fr_collector.ingest(conn, self.correction, source="published")

    def report(self, **kwargs):
        arguments = {
            "document_numbers": ["2026-19391", "2026-21995"],
            "as_of": "2026-10-28",
        }
        arguments.update(kwargs)
        return dates.build_timeline(self.source_db, self.graph_db, **arguments)

    def make_link(self):
        kg.import_federal_register(self.graph_db, self.source_db, "2026-19391")
        corrected = kg.import_federal_register(
            self.graph_db, self.source_db, "2026-21995")
        kg.add_node(self.graph_db, node_id="frdoc:2026-19391",
                    kind="PUBLICATION", label="Original", source_db=self.source_db)
        kg.add_node(self.graph_db, node_id="frdoc:2026-21995",
                    kind="PUBLICATION", label="Correction", source_db=self.source_db)
        kg.add_edge(
            self.graph_db, from_id="frdoc:2026-21995",
            to_id="frdoc:2026-19391", predicate="CORRECTS",
            doc_id=corrected["id"], excerpt=self.quote,
            locator="Synthetic metadata abstract", actor="Internal test researcher",
            source_db=self.source_db)

    def test_separates_publication_date_from_stated_effective_date(self):
        report = self.report()
        first, second = report["documents"]
        self.assertEqual(first["publication_date"], "2026-09-22")
        self.assertEqual(first["stated_effective_on"], "2026-12-24")
        self.assertEqual(first["effective_date_relative_to_as_of"],
                         "AFTER_AS_OF_NOT_LEGAL_STATUS")
        self.assertEqual(second["publication_date"], "2026-10-28")
        self.assertEqual(len(report["timeline_events"]), 4)
        self.assertEqual(report["compliance_status"], "NOT_DETERMINED")
        self.assertFalse(report["external_release_authorized"])

    def test_missing_effective_date_has_no_publication_date_fallback(self):
        with closing(sqlite3.connect(self.source_db)) as conn:
            fr_collector.ingest(conn, {**self.original, "effective_on": None},
                                source="published")
        first = self.report(document_numbers=["2026-19391"])["documents"][0]
        self.assertIsNone(first["stated_effective_on"])
        self.assertEqual(first["effective_date_status"], "MISSING_REQUIRES_REVIEW")
        self.assertEqual(first["effective_date_relative_to_as_of"], "UNDETERMINED")

    def test_invalid_effective_date_is_flagged_not_interpreted(self):
        with closing(sqlite3.connect(self.source_db)) as conn:
            fr_collector.ingest(conn, {**self.original, "effective_on": "2026-02-30"},
                                source="published")
        first = self.report(document_numbers=["2026-19391"])["documents"][0]
        self.assertIsNone(first["stated_effective_on"])
        self.assertEqual(first["effective_date_status"], "INVALID_REQUIRES_REVIEW")

    def test_collector_metadata_update_is_not_formal_amendment(self):
        with closing(sqlite3.connect(self.source_db)) as conn:
            fr_collector.ingest(conn, {**self.original, "title": "Changed metadata"},
                                source="published")
        first = self.report(document_numbers=["2026-19391"])["documents"][0]
        self.assertEqual(len(first["source_version_history"]), 2)
        self.assertTrue(all(x["integrity"] == "PIN_MATCH"
                            for x in first["source_version_history"]))
        self.assertEqual(first["formal_amendment_status"], "NOT_DETERMINED")

    def test_valid_correction_candidate_remains_research_only(self):
        self.make_link()
        report = self.report()
        self.assertEqual(len(report["correction_candidates"]), 1)
        link = report["correction_candidates"][0]
        self.assertEqual(link["earlier_document_number"], "2026-19391")
        self.assertEqual(link["relationship_state"], "PROPOSED_RESEARCH_ONLY")
        self.assertEqual(link["evidence_status"], dates.PIN_OK)
        self.assertFalse(link["regulatory_effect_determined"])
        self.assertFalse(report["human_review_complete"])

    def test_changed_original_pin_flags_existing_candidate(self):
        self.make_link()
        with closing(sqlite3.connect(self.source_db)) as conn:
            fr_collector.ingest(conn, {**self.original, "title": "Revised metadata"},
                                source="published")
        link = self.report()["correction_candidates"][0]
        self.assertEqual(link["evidence_status"],
                         "NEWER_ORIGINAL_METADATA_REQUIRES_REVIEW")
        self.assertTrue(link["requires_evidence_refresh"])

    def test_no_graph_does_not_mean_no_corrections_exist(self):
        report = self.report()
        self.assertEqual(report["graph_status"], "GRAPH_NOT_AVAILABLE")
        self.assertEqual(report["correction_candidates"], [])
        self.assertEqual(report["formal_amendment_status"], "NOT_DETERMINED")

    def test_invalid_document_and_as_of_are_rejected(self):
        with self.assertRaises(ValueError):
            self.report(document_numbers=["not-a-document"])
        with self.assertRaises(ValueError):
            self.report(as_of="2026-13-35")
        with self.assertRaises(ValueError):
            self.report(limit=0)

    def test_public_inspection_only_cannot_pass_for_published(self):
        with closing(sqlite3.connect(self.source_db)) as conn:
            fr_collector.ingest(conn, {
                **self.original, "document_number": "2026-29999",
            }, source="public_inspection")
        with self.assertRaises(ValueError):
            self.report(document_numbers=["2026-29999"])

    def test_date_parser_rejects_timestamps_and_invalid_days(self):
        self.assertEqual(dates.parse_date("2026-10-28")[1], "METADATA_DATE_ONLY")
        for value in ["2026-10-28T00:00:00Z", "2026-02-30", 20261028, "today"]:
            with self.subTest(value=value):
                self.assertEqual(dates.parse_date(value),
                                 (None, "INVALID_REQUIRES_REVIEW"))

    def test_latest_only_and_deduplicated_document_selection(self):
        report = self.report(document_numbers=["2026-19391", "2026-19391"])
        self.assertEqual(len(report["documents"]), 1)
        latest = dates.build_timeline(self.source_db, self.graph_db,
                                      document_numbers=None, as_of="2026-10-28")
        self.assertEqual(len(latest["documents"]), 2)

    def test_collector_remains_read_only(self):
        with closing(sqlite3.connect(self.source_db)) as conn:
            before = conn.execute("SELECT COUNT(*) FROM document_snapshots").fetchone()[0]
        self.report()
        with closing(sqlite3.connect(self.source_db)) as conn:
            after = conn.execute("SELECT COUNT(*) FROM document_snapshots").fetchone()[0]
        self.assertEqual(before, after)

    def test_offline_command_json_and_safety_fields(self):
        stream = io.StringIO()
        with redirect_stdout(stream):
            result = dates.main(["--source-db", str(self.source_db),
                                 "--graph-db", str(self.graph_db),
                                 "--as-of", "2026-10-28",
                                 "--document-number", "2026-19391"])
        self.assertEqual(result, 0)
        self.assertIn('"external_release_authorized": false', stream.getvalue())


if __name__ == "__main__":
    unittest.main()
