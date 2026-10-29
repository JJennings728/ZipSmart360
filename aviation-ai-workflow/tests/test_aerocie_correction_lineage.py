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
                         'LOCAL_METADATA_PIN_MATCH_ONLY_NOT_CURRENT_AUTHORITY')

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


if __name__ == '__main__':
    unittest.main()
