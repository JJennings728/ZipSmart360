"""AeroCIE-009 regression tests. Fully offline with synthetic records."""
from contextlib import closing, redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from src.aerocie import knowledge_graph as kg
from src.aerocie.fr_collector import initialize as init_collector, ingest


class KnowledgeGraphTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.db = root / 'kg.sqlite3'
        self.source_db = root / 'fr.sqlite3'
        self.source_file = root / 'synthetic.txt'
        self.source_file.write_text('SYNTHETIC DEMO. Example aircraft appears in an example memo.\n', encoding='utf-8')
        kg.import_text(self.db, doc_id='doc:synthetic:1', title='Synthetic demonstration',
                       url='https://example.invalid/demo', text=self.source_file.read_text(),
                       source_db=self.source_db)
        kg.add_node(self.db, node_id='aircraft:fictional', kind='AIRCRAFT',
                    label='Fictional aircraft', source_db=self.source_db)
        kg.add_node(self.db, node_id='topic:example', kind='TOPIC',
                    label='Synthetic memo', source_db=self.source_db)

    def add(self, **updates):
        args=dict(from_id='aircraft:fictional', to_id='topic:example', predicate='MENTIONS',
                  doc_id='doc:synthetic:1', excerpt='Example aircraft appears',
                  locator='Synthetic text | line 1', actor='SRP internal researcher', source_db=self.source_db)
        args.update(updates)
        return kg.add_edge(self.db, **args)

    def test_pinned_document_and_export(self):
        self.add()
        out=kg.export_graph(self.db,self.source_db)
        self.assertEqual((len(out['nodes']),len(out['edges']),len(out['documents'])),(2,1,1))
        self.assertEqual(out['edges'][0]['evidence_status'], 'PINNED_LOCAL_TEXT_MATCH_ONLY_NOT_LIVE_VERIFIED')
        self.assertEqual(out['edges'][0]['sha256'], hashlib.sha256(self.source_file.read_bytes()).hexdigest())
        self.assertEqual(out['compliance_status'],'NOT_DETERMINED')
        self.assertFalse(out['external_release_authorized'])

    def test_link_requires_exact_quote(self):
        with self.assertRaises(ValueError):self.add(excerpt='claim not in source')
        self.assertEqual(kg.export_graph(self.db,self.source_db)['edges'],[])

    def test_research_only_predicates(self):
        for predicate in ('COMPLIANT_WITH', 'MANDATES', 'PROHIBITS'):
            with self.subTest(predicate=predicate), self.assertRaises(ValueError):
                self.add(predicate=predicate)

    def test_reject_unknown_nodes_and_self_links(self):
        with self.assertRaises(sqlite3.IntegrityError):self.add(to_id='topic:missing')
        with self.assertRaises(ValueError):self.add(to_id='aircraft:fictional')

    def test_duplicate_edges_fail(self):
        self.add()
        with self.assertRaises(sqlite3.IntegrityError):self.add()

    def test_id_is_immutable(self):
        kg.import_text(self.db,doc_id='doc:synthetic:1',title='Synthetic demonstration',
                       url='https://example.invalid/demo',text=self.source_file.read_text(),
                       source_db=self.source_db)
        with self.assertRaises(ValueError):
            kg.import_text(self.db,doc_id='doc:synthetic:1',title='Edited',
                           url='https://example.invalid/demo',text='Changed source', source_db=self.source_db)
        with self.assertRaises(ValueError):
            kg.add_node(self.db,node_id='topic:example',kind='TOPIC',label='Changed',source_db=self.source_db)

    def test_tamper_content_flagged_and_new_link_rejected(self):
        self.add()
        with closing(sqlite3.connect(self.db)) as conn:
            conn.execute("UPDATE kg_documents SET content='manipulated' WHERE id='doc:synthetic:1'")
            conn.commit()
        out=kg.export_graph(self.db,self.source_db)['edges'][0]
        self.assertEqual(out['evidence_status'],'PINNED_EVIDENCE_INTEGRITY_FAILURE')
        self.assertFalse(out['external_release_authorized'])
        with self.assertRaises(ValueError):self.add(excerpt='manipulated')

    def test_evidence_quote_tamper_detected(self):
        self.add()
        with closing(sqlite3.connect(self.db)) as conn:
            conn.execute("UPDATE kg_edges SET exact_excerpt='NONEXISTENT'")
            conn.commit()
        self.assertEqual(kg.evidence_edges(self.db,self.source_db)[0]['evidence_status'],
                         'EXCERPT_MISSING_FROM_PINNED_EVIDENCE')

    def test_graph_neighbors(self):
        self.add()
        self.assertEqual(len(kg.export_graph(self.db,self.source_db,'aircraft:fictional')['edges']),1)
        self.assertEqual(len(kg.export_graph(self.db,self.source_db,'topic:example')['edges']),1)
        with self.assertRaises(ValueError):
            kg.export_graph(self.db,self.source_db,'topic:does-not-exist')

    def test_injection_controlled(self):
        with self.assertRaises(ValueError):kg.add_node(self.db,node_id='../oops',kind='OTHER',label='X',source_db=self.source_db)
        with self.assertRaises(ValueError):kg.import_text(self.db,doc_id='doc:invalid',title='x',url='file:///etc/passwd',text='x',source_db=self.source_db)
        with self.assertRaises(ValueError):kg.import_text(self.db,doc_id='doc:invalid',title='x',url='https://u:p@example.com/foo',text='x',source_db=self.source_db)

    def test_html_escapes_script_payload(self):
        kg.add_node(self.db,node_id='topic:unsafe',kind='TOPIC',label='</script><script>alert(1)</script>',source_db=self.source_db)
        self.add()
        page=kg.render_html(kg.export_graph(self.db,self.source_db))
        self.assertIn('\\u003c/script\\u003e',page)
        self.assertNotIn('</script><script>alert(1)',page)
        self.assertIn('INTERNAL RESEARCH ONLY',page)

    def test_source_db_guard(self):
        with closing(sqlite3.connect(self.source_db)) as conn:
            init_collector(conn)
        with self.assertRaises(ValueError):kg.initialize(self.source_db,self.source_db)
        with self.assertRaises(ValueError):kg.initialize(self.source_db,self.db)

    def _fr(self):
        self.doc_num='2026-21290'
        self.row={'document_number':self.doc_num, 'title':'SYNTHETIC | Example title',
                  'type':'Rule','publication_date':'2026-10-25',
                  'html_url':'https://www.federalregister.gov/documents/2026/10/25/2026-21290/synthetic'}
        with closing(sqlite3.connect(self.source_db)) as conn:
            init_collector(conn); ingest(conn,self.row,source='published')
        kg.import_federal_register(self.db,self.source_db,self.doc_num)
        doc_id=kg.export_graph(self.db,self.source_db)['documents'][1]['id']
        return doc_id

    def test_fr_metadata_fingerprint_and_freshness(self):
        doc_id=self._fr()
        kg.add_edge(self.db,from_id='aircraft:fictional',to_id='topic:example',predicate='REFERENCES',
                    doc_id=doc_id,excerpt='SYNTHETIC | Example title',locator='metadata | title',
                    actor='SRP Research',source_db=self.source_db)
        self.assertEqual(kg.evidence_edges(self.db,self.source_db)[0]['evidence_status'],
                         'LOCAL_METADATA_PIN_MATCH_ONLY_NOT_CURRENT_AUTHORITY')
        with closing(sqlite3.connect(self.source_db)) as conn:
            ingest(conn,{**self.row,'title':'New local snapshot'},source='published')
        self.assertEqual(kg.evidence_edges(self.db,self.source_db)[0]['evidence_status'],
                         'NEWER_LOCAL_METADATA_REQUIRES_REVIEW')

    def test_fr_absent_source_fails_closed(self):
        doc_id=self._fr()
        kg.add_edge(self.db,from_id='aircraft:fictional',to_id='topic:example',predicate='REFERENCES',
                    doc_id=doc_id,excerpt='SYNTHETIC | Example title',locator='metadata | title',
                    actor='SRP Research',source_db=self.source_db)
        self.source_db.unlink()
        self.assertEqual(kg.evidence_edges(self.db,self.source_db)[0]['evidence_status'],
                         'PINNED_FEDERAL_REGISTER_METADATA_UNAVAILABLE_OR_INVALID')

    def test_cli_envelope(self):
        out=io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(kg.main(['--db',str(self.db),'--source-db',str(self.source_db),'stats']),0)
        parsed=json.loads(out.getvalue())
        self.assertEqual(parsed['compliance_status'],'NOT_DETERMINED')
        self.assertFalse(parsed['external_release_authorized'])


if __name__ == '__main__':unittest.main()