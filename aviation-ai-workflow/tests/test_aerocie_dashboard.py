"""AeroCIE-005 dashboard regression tests. Safe on Windows: explicit SQLite closing."""
from __future__ import annotations
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from src.aerocie.fr_collector import ingest, initialize
from src.aerocie.dashboard import (
    make_handler, read_cached_evidence, render_index, render_document,
    safe_external, load_reviews, normalize_filters, h,
)
from src.aerocie.full_text_review import write_evidence


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name)/'federal_register.sqlite3'
        self.evidence = Path(self.tmp.name)/'evidence'
        self.final = {
            'document_number':'2024-06419','title':'Airworthiness Directives; International Aero Engines, LLC Engines',
            'type':'RULE','action':'Final rule.', 'publication_date':'2024-03-27',
            'effective_on':'2024-04-11','dates':'This AD is effective April 11, 2024.',
            'abstract':'Some PW1100G series engine models and PW1400G.',
            'html_url':'https://www.federalregister.gov/documents/2024/03/27/2024-06419/some-title',
            'pdf_url':'https://www.govinfo.gov/content/pkg/FR-2024-03-27/pdf/2024-06419.pdf',
            'docket_ids':['Docket No. FAA-2023-2401'],
        }
        self.proposal = {
            'document_number':'2026-21298','title':'PW4000 Proposal & Review',
            'type':'PRORULE','action':'Proposed rule.','publication_date':'2026-10-19',
            'html_url':'https://www.federalregister.gov/documents/2026/10/19/2026-21298/title'
        }
        with closing(sqlite3.connect(self.db)) as conn:
            initialize(conn)
            ingest(conn,self.final,source='published')
            ingest(conn,self.proposal,source='published')
            conn.commit()

    def cache_text(self, content: bytes):
        from src.aerocie.fr_collector import canonical_record
        doc = canonical_record(self.final,source='published')
        write_evidence(self.evidence,doc,
            'https://www.federalregister.gov/documents/full_text/text/2024/03/27/2024-06419.txt',
            content,retrieved_at='2026-10-20T19:00:00+00:00')

    def test_index_counts_and_categories(self):
        page = render_index(self.db,self.evidence,{'as_of':['2026-10-20']})
        self.assertIn('2024-06419',page)
        self.assertIn('2026-21298',page)
        self.assertIn('proposed rule',page)
        self.assertIn('Published rules',page)
        self.assertIn('No FAA certification',page)

    def test_filter_publications(self):
        results, _, truncated = load_reviews(self.db,category='proposed_rule',as_of='2026-10-20')
        self.assertEqual(len(results),1)
        self.assertEqual(results[0]['document_number'],'2026-21298')
        self.assertFalse(truncated)

    def test_metadata_model_not_legal_verdict(self):
        page=render_index(self.db,self.evidence,{'model':['PW1100G'],'as_of':['2026-10-20']})
        self.assertIn('model explicitly mentioned in stored metadata',page)
        self.assertIn('never a clearance',page)

    def test_html_escape(self):
        self.assertEqual(h('<script>alert(1)</script>'),'&lt;script&gt;alert(1)&lt;/script&gt;')
        page=render_index(self.db,self.evidence,{'q':['<img src=x onerror=alert(1)>']})
        self.assertNotIn('<img src=x',page)
        self.assertIn('&lt;img src=x',page)

    def test_invalid_model(self):
        with self.assertRaises(ValueError):
            normalize_filters({'model':['.*']})

    def test_bad_external_url_rejected(self):
        self.assertIsNone(safe_external('http://www.federalregister.gov/test'))
        self.assertIsNone(safe_external('https://www.federalregister.gov.evil.com/test'))
        self.assertIsNone(safe_external('https://username@www.federalregister.gov/test'))
        self.assertIsNotNone(safe_external(self.final['html_url']))

    def test_no_cache_is_explicit(self):
        page=render_document(self.db,self.evidence,'2024-06419',{'model':['PW1100G']})
        self.assertIn('No local full-text copy saved',page)
        self.assertIn('unverified',page)

    def test_verified_cache_and_variant_candidates(self):
        self.cache_text(b'Background\n(c) Applicability\n(1) This AD applies to Model PW1127G-JM, PW1133G-JM engines with installed HPC items.\n(d) Subject\nPW1100G series engines.\n')
        result=read_cached_evidence(self.evidence,'2024-06419')
        self.assertEqual(result['state'],'hash_verified_local_cache')
        page=render_document(self.db,self.evidence,'2024-06419',{'model':['PW1100G']})
        self.assertIn('PW1127G-JM',page)
        self.assertIn('Variant candidates',page)
        self.assertIn('SHA-256:',page)

    def test_hash_tamper_is_reported_not_read(self):
        self.cache_text(b'Original official-like example')
        path=next((self.evidence/'2024-06419').glob('*.txt'))
        path.write_bytes(b'TAMPERED')
        self.assertEqual(read_cached_evidence(self.evidence,'2024-06419')['state'],'hash_mismatch')
        page=render_document(self.db,self.evidence,'2024-06419',{'model':['PW1100G']})
        self.assertIn('hash mismatch',page.lower())
        self.assertNotIn('TAMPERED',page)

    def test_rendering_does_not_change_database(self):
        before=hashlib.sha256(self.db.read_bytes()).hexdigest()
        render_index(self.db,self.evidence,{'model':['PW1100G']})
        render_document(self.db,self.evidence,'2024-06419',{'model':['PW1100G']})
        after=hashlib.sha256(self.db.read_bytes()).hexdigest()
        self.assertEqual(before,after)

    def test_invalid_document_id(self):
        with self.assertRaises(ValueError):
            render_document(self.db,self.evidence,'../',{})

    def test_loopback_http_host_and_post(self):
        server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(self.db,self.evidence,port=0))
        # Make handler check the actual ephemeral port.
        server.server_close()
        server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(self.db,self.evidence,port=8766))
        # Port-specific host check intentionally tested by explicitly setting a correct Host value.
        th=threading.Thread(target=server.serve_forever,daemon=True)
        th.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        url=f'http://127.0.0.1:{server.server_port}/'
        r=urllib.request.Request(url,headers={'Host':'localhost:8766'})
        with urllib.request.urlopen(r,timeout=3) as response:
            self.assertEqual(response.status,200)
            self.assertIn('No FAA certification',response.read().decode())
        r=urllib.request.Request(url,headers={'Host':'evil.example'})
        with self.assertRaises(urllib.error.HTTPError) as err:
            urllib.request.urlopen(r,timeout=3)
        self.assertEqual(err.exception.code,403)
        post=urllib.request.Request(url,data=b'payload',headers={'Host':'localhost:8766'},method='POST')
        with self.assertRaises(urllib.error.HTTPError) as err:
            urllib.request.urlopen(post,timeout=3)
        self.assertEqual(err.exception.code,405)


if __name__ == '__main__':
    unittest.main()
