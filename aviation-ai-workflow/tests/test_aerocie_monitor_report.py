"""Offline checks; no Federal Register HTTP calls and no customer data."""
from __future__ import annotations

import json
from contextlib import closing
import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.aerocie import monitor, report
from src.aerocie.fr_collector import initialize, ingest


def sample(doc='2026-21290', title='Airworthiness Directives; Sample Engine', typ='Rule'):
    return {
        'document_number': doc,
        'title': title, 'type': typ, 'publication_date': '2026-10-19',
        'effective_on': '2026-11-23' if typ == 'Rule' else None,
        'abstract': 'Sample only', 'action': 'Final rule.' if typ == 'Rule' else 'NPRM',
        'dates': 'This AD is effective November 23, 2026.' if typ == 'Rule' else 'Comments due December 3, 2026.',
        'docket_ids': ['FAA-2026-0001'],
        'html_url': 'https://www.federalregister.gov/documents/2026/10/19/2026-21290/sample',
        'pdf_url': 'https://www.govinfo.gov/content/pkg/FR-2026-10-19/pdf/2026-21290.pdf',
    }


def fake_api(rows, inspection=None):
    def fetch(path, params=None, **kwargs):
        if path == 'documents.json':
            return {'results': rows}
        if path == 'public-inspection-documents.json':
            return {'results': inspection or []}
        raise AssertionError(path)
    return fetch


class MonitorAndReportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.db = self.folder / 'federal_register.sqlite3'

    def test_baseline_and_unchanged_again(self):
        fetch = fake_api([sample()])
        first = monitor.run_monitor(db=self.db, since='2026-10-01', get_json=fetch)
        self.assertTrue(first['baseline_created'])
        self.assertEqual(first['new_to_database'], 1)
        self.assertEqual(first['review_items'][0]['publication_category'], 'rule')
        self.assertFalse(first['notifications_sent'])
        second = monitor.run_monitor(db=self.db, since='2026-10-01', get_json=fetch)
        self.assertFalse(second['baseline_created'])
        self.assertEqual((second['new_to_database'], second['metadata_changed'], second['unchanged']), (0, 0, 1))

    def test_change_events_preserved(self):
        monitor.run_monitor(db=self.db, since='2026-10-01', get_json=fake_api([sample()]))
        changed = monitor.run_monitor(db=self.db, since='2026-10-01', get_json=fake_api([sample(title='Changed title')]))
        self.assertEqual(changed['metadata_changed'], 1)
        self.assertEqual(changed['review_items'][0]['monitor_event'], 'metadata_changed')
        with closing(sqlite3.connect(self.db)) as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM document_snapshots').fetchone()[0], 2)

    def test_proposal_not_a_rule(self):
        r = monitor.run_monitor(db=self.db, since='2026-10-01', get_json=fake_api([sample(typ='Proposed Rule')]))
        self.assertEqual(r['review_items'][0]['publication_category'], 'proposed_rule')
        self.assertEqual(r['review_items'][0]['triage_status'], 'proposal_not_an_adopted_final_rule')

    def test_api_fail_has_no_database_side_effect(self):
        def broken(*args, **kwargs):
            raise RuntimeError('unreachable')
        with self.assertRaises(RuntimeError):
            monitor.run_monitor(db=self.db, since='2026-10-01', get_json=broken)
        self.assertFalse(self.db.exists())

    def test_inspection_failure_has_no_partial_write(self):
        def broken_second(path, params=None):
            if path == 'documents.json':
                return {'results':[sample()]}
            raise RuntimeError('inspection unavailable')
        with self.assertRaises(RuntimeError):
            monitor.run_monitor(db=self.db, since='2026-10-01', include_inspection=True, get_json=broken_second)
        self.assertFalse(self.db.exists())

    def test_inspection_staged_separately(self):
        r = monitor.run_monitor(db=self.db, since='2026-10-01', include_inspection=True,
                                get_json=fake_api([sample()], [sample(doc='2026-21291', typ='Proposed Rule')]))
        self.assertEqual(r['inspection_checked'], 1)
        item = next(x for x in r['review_items'] if x['source']=='public_inspection')
        self.assertEqual(item['triage_status'],'public_inspection_not_published')

    def test_cap_flag_not_silent_clearance(self):
        r = monitor.run_monitor(db=self.db, since='2026-10-01', limit=1, get_json=fake_api([sample()]))
        self.assertFalse(r['scan_complete'])
        self.assertTrue(r['warnings'])

    def test_save_run_and_draft_html(self):
        r = monitor.run_monitor(db=self.db, since='2026-10-01', get_json=fake_api([sample()]))
        jp, hp = monitor.save_run(r,directory=self.folder/'reports')
        self.assertTrue(jp.exists())
        self.assertTrue(hp.exists())
        self.assertIn('HUMAN REVIEW REQUIRED', hp.read_text(encoding='utf8'))
        self.assertEqual(json.loads(jp.read_text(encoding='utf8'))['new_to_database'], 1)
        jp2,hp2 = monitor.save_run(r,directory=self.folder/'reports')
        self.assertNotEqual(jp,jp2)
        self.assertNotEqual(hp,hp2)

    def test_monitor_limit_and_date_validations(self):
        for limit in (0, 501):
            with self.assertRaises(ValueError):
                monitor.run_monitor(db=self.db, since='2026-10-01', limit=limit, get_json=fake_api([]))
        with self.assertRaises(ValueError):
            monitor.run_monitor(db=self.db, since='2026-99-99', get_json=fake_api([]))

    def test_reports_read_only_and_print_ready(self):
        with closing(sqlite3.connect(self.db)) as conn:
            initialize(conn)
            ingest(conn,sample(),source='published')
        before=self.db.read_bytes()
        out=self.folder/'report.html'
        r=report.create_report(self.db,out=out,keyword='Engine',as_of='2026-10-20')
        self.assertEqual(r['records'],1)
        self.assertIn('@media print',out.read_text(encoding='utf8'))
        self.assertIn('Official PDF',out.read_text(encoding='utf8'))
        self.assertEqual(before,self.db.read_bytes())

    def test_html_escapes_untrusted_metadata(self):
        dangerous='<script>alert("boom")</script>'
        raw={'title': dangerous, 'document_number': '2026-21290', 'source_url': 'javascript:alert(1)',
             'official_pdf_url': 'https://www.govinfo.gov/file.pdf', 'publication_category': 'rule',
             'docket_ids': ['<img onerror=alert(1)>']}
        content=report.render_report([raw],as_of='2026-10-20',report_title=dangerous)
        self.assertNotIn('<script>',content)
        self.assertNotIn('href="javascript:',content)
        self.assertNotIn('<img onerror=',content)
        self.assertIn('&lt;script&gt;',content)

    def test_only_trusted_https_source_links(self):
        for url in ('http://www.govinfo.gov/a','https://govinfo.gov.evil.com/a',
                    'https://attacker@www.govinfo.gov/a', 'javascript:alert(1)',
                    'https://www.govinfo.gov:444/a'):
            self.assertEqual(report.safe_source_link(url,'PDF'),'',url)
        self.assertIn('href="https://www.govinfo.gov/a"',report.safe_source_link('https://www.govinfo.gov/a','PDF'))

    def test_empty_report_is_not_clearance(self):
        content=report.render_report([],as_of='2026-10-20')
        self.assertIn('not a regulatory clearance',content)

    def test_invalid_date_and_limit(self):
        with self.assertRaises(ValueError):
            report.render_report([],as_of='2026-20-40')
        with self.assertRaises(ValueError):
            report.create_report(self.db,out=self.folder/'report.html',limit=5000)


if __name__ == '__main__':
    unittest.main()
