"""Research-only correction lineage guardrails; synthetic/offline fixtures only."""
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
import sqlite3
import unittest

from src.aerocie import fr_collector, knowledge_graph as kg


class CorrectionLineageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.src = root / 'federal_register.sqlite3'
        self.graph = root / 'knowledge_graph.sqlite3'
        original = {
            'document_number': '2026-19391',
            'title': 'Establishment of Class E Airspace; Ottawa, IL',
            'type': 'Rule', 'publication_date': '2026-09-22',
            'effective_on': '2026-12-24',
            'abstract': 'Establishes Class E airspace.',
            'action': 'Final rule.',
            'docket_ids': ['Docket No. FAA-2026-8548'],
            'citation': '91 FR 59987',
            'html_url': 'https://www.federalregister.gov/documents/2026/09/22/2026-19391/test',
        }
        self.quote = ('This action corrects a final rule published by the FAA '
                      'in the Federal Register on September 22, 2026.')
        correction = {
            'document_number': '2026-21995',
            'title': 'Establishment of Class E Airspace; Ottawa, IL; Correction',
            'type': 'Rule', 'publication_date': '2026-10-28',
            'effective_on': '2026-12-24',
            'abstract': self.quote,
            'action': 'Final rule; correction.',
            'docket_ids': ['Docket No. FAA-2026-8548'],
            'citation': '91 FR 67769',
            'html_url': 'https://www.federalregister.gov/documents/2026/10/28/2026-21995/test',
        }
        with closing(sqlite3.connect(self.src)) as conn:
            fr_collector.initialize(conn)
            fr_collector.ingest(conn, original, source='published')
            fr_collector.ingest(conn, correction, source='published')
        self.old = kg.import_federal_register(self.graph, self.src, '2026-19391')['id']
        self.new = kg.import_federal_register(self.graph, self.src, '2026-21995')['id']
        kg.add_node(self.graph, node_id='frdoc:2026-19391', kind='PUBLICATION',
                    label='Original rule', source_db=self.src)
        kg.add_node(self.graph, node_id='frdoc:2026-21995', kind='PUBLICATION',
                    label='Correction', source_db=self.src)

    def link(self, **overrides):
        args = {
            'db': self.graph, 'source_db': self.src,
            'from_id': 'frdoc:2026-21995', 'to_id': 'frdoc:2026-19391',
            'predicate': 'CORRECTS', 'doc_id': self.new,
            'excerpt': self.quote, 'locator': 'Published metadata | summary',
            'actor': 'SRP internal research',
        }
        args.update(overrides)
        return kg.add_edge(**args)

    def test_supported_correction_is_proposed_not_approved(self):
        result = self.link()
        self.assertEqual(result['state'], 'PROPOSED_RESEARCH_ONLY')
        exported = kg.export_graph(self.graph, self.src)
        self.assertFalse(exported['external_release_authorized'])
        self.assertEqual(exported['compliance_status'], 'NOT_DETERMINED')
        self.assertEqual(exported['edges'][0]['predicate'], 'CORRECTS')
        self.assertEqual(exported['edges'][0]['evidence_status'],
                         'LOCAL_BOTH_METADATA_PINS_MATCH_ONLY_NOT_CURRENT_AUTHORITY')

    def test_reverse_direction_is_rejected(self):
        with self.assertRaises(ValueError):
            self.link(from_id='frdoc:2026-19391', to_id='frdoc:2026-21995')

    def test_wrong_evidence_document_rejected(self):
        with self.assertRaises(ValueError):
            self.link(doc_id=self.old)

    def test_excerpt_must_reference_original(self):
        with self.assertRaises(ValueError):
            self.link(excerpt='Final rule; correction.')

    def test_mismatched_publication_node_rejected(self):
        kg.add_node(self.graph, node_id='topic:airspace', kind='TOPIC',
                    label='Airspace', source_db=self.src)
        with self.assertRaises(ValueError):
            self.link(to_id='topic:airspace')

    def test_missing_source_snapshot_fail_closed(self):
        with closing(sqlite3.connect(self.src)) as conn:
            with conn:
                conn.execute("DELETE FROM document_snapshots WHERE document_number='2026-19391'")
        with self.assertRaises(ValueError):
            self.link()

    def test_duplicate_correction_is_blocked(self):
        self.link()
        with self.assertRaises(sqlite3.IntegrityError):
            self.link()


    def _update_original_snapshot(self):
        original = kg.snapshot(self.src, '2026-19391')['record']
        newer = {**original, 'title': original['title'] + ' | revised metadata'}
        with closing(sqlite3.connect(self.src)) as conn:
            with conn:
                fr_collector.ingest(conn, newer, source='published')
        return newer

    def test_original_fingerprint_persisted_and_exported(self):
        result = self.link()
        with closing(sqlite3.connect(self.graph)) as conn:
            row = conn.execute(
                'SELECT original_document_id, original_document_sha256 '
                'FROM kg_correction_pins WHERE edge_id=?',
                (result['id'],)).fetchone()
        self.assertEqual(row[0], self.old)
        self.assertEqual(row[1], kg.snapshot(self.src, '2026-19391')['fingerprint'])
        edge = kg.export_graph(self.graph, self.src)['edges'][0]
        self.assertEqual(edge['original_document_id'], self.old)
        self.assertEqual(edge['original_document_sha256'], row[1])

    def test_original_change_is_flagged_after_link_creation(self):
        self.link()
        self._update_original_snapshot()
        edge = kg.export_graph(self.graph, self.src)['edges'][0]
        self.assertEqual(edge['evidence_status'], 'NEWER_ORIGINAL_METADATA_REQUIRES_REVIEW')

    def test_refresh_of_original_keeps_old_evidence(self):
        self._update_original_snapshot()
        refreshed = kg.import_federal_register(self.graph, self.src, '2026-19391')
        self.assertNotEqual(refreshed['id'], self.old)
        result = self.link()
        with closing(sqlite3.connect(self.graph)) as conn:
            row = conn.execute('SELECT original_document_id FROM kg_correction_pins '
                               'WHERE edge_id=?', (result['id'],)).fetchone()
        self.assertEqual(row[0], refreshed['id'])
        self.assertEqual(kg.export_graph(self.graph, self.src)['edges'][0]['evidence_status'],
                         'LOCAL_BOTH_METADATA_PINS_MATCH_ONLY_NOT_CURRENT_AUTHORITY')

    def test_refresh_without_import_rejected(self):
        self._update_original_snapshot()
        with self.assertRaises(ValueError):
            self.link()

    def test_missing_original_collector_snapshot_flags_link(self):
        self.link()
        with closing(sqlite3.connect(self.src)) as conn:
            with conn:
                conn.execute("DELETE FROM document_snapshots WHERE document_number='2026-19391'")
        self.assertEqual(kg.export_graph(self.graph, self.src)['edges'][0]['evidence_status'],
                         'PINNED_ORIGINAL_METADATA_UNAVAILABLE_OR_INVALID')

    def test_original_graph_document_tampering_flags_link(self):
        self.link()
        with closing(sqlite3.connect(self.graph)) as conn:
            with conn:
                conn.execute('UPDATE kg_documents SET content=? WHERE id=?', ('{}', self.old))
        self.assertEqual(kg.export_graph(self.graph, self.src)['edges'][0]['evidence_status'],
                         'PINNED_ORIGINAL_EVIDENCE_INTEGRITY_FAILURE')

    def test_legacy_link_missing_original_pin_requires_review(self):
        self.link()
        with closing(sqlite3.connect(self.graph)) as conn:
            with conn:
                conn.execute('DELETE FROM kg_correction_pins')
        self.assertEqual(kg.export_graph(self.graph, self.src)['edges'][0]['evidence_status'],
                         'ORIGINAL_PIN_MISSING_REQUIRES_REVIEW')

    def test_non_correction_evidence_status_unchanged(self):
        kg.add_edge(self.graph, from_id='frdoc:2026-21995',
                    to_id='frdoc:2026-19391', predicate='MENTIONS',
                    doc_id=self.new, excerpt=self.quote, locator='Metadata abstract',
                    actor='SRP research', source_db=self.src)
        self.assertEqual(kg.export_graph(self.graph, self.src)['edges'][0]['evidence_status'],
                         'LOCAL_METADATA_PIN_MATCH_ONLY_NOT_CURRENT_AUTHORITY')

if __name__ == '__main__':
    unittest.main()
