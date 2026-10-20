"""AeroCIE-004 offline unit tests; no Federal Register network requests."""
from __future__ import annotations

import hashlib
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from src.aerocie.full_text_review import (
    applicability_spans, download_text, raw_text_url, read_published_snapshot,
    run, screen_full_text, write_evidence,
)


DOCUMENT = {
    'source': 'published',
    'document_number': '2024-06419',
    'title': 'Airworthiness Directives; International Aero Engines, LLC Engines',
    'document_type': 'Rule',
    'publication_date': '2024-03-27',
    'effective_on': '2024-04-11',
    'dates_text': 'This AD is effective April 11, 2024.',
    'html_url': 'https://www.federalregister.gov/documents/2024/03/27/2024-06419/example',
    'pdf_url': 'https://www.govinfo.gov/content/pkg/FR-2024-03-27/pdf/2024-06419.pdf',
    'raw_text_url': 'https://www.federalregister.gov/documents/full_text/text/2024/03/27/2024-06419.txt',
}
DOCUMENT_BODY = b'''Federal Aviation Administration\nAirworthiness Directives\n\n(c) Applicability\nThis AD applies to certain Model PW1100G series engines.\nAn applicability mention must be checked against engine serials.\n\n(d) Subject\nPowerplant.\n\n(e) Unsafe Condition\nA PW1100G2 model mention here is not an exact match for the target model.\n\n(f) Compliance\nComply within required times unless already done.\n'''


class FullTextTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.db = self.root / 'federal_register.sqlite3'
        self.evidence_dir = self.root / 'evidence'
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.execute('''CREATE TABLE document_snapshots
                (id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT, document_number TEXT,
                 payload_json TEXT)''')
            conn.execute('INSERT INTO document_snapshots(source, document_number, payload_json) VALUES (?, ?, ?)',
                         ('published', '2024-06419', json.dumps(DOCUMENT)))
        self.original_bytes = self.db.read_bytes()

    def test_safe_url(self):
        self.assertEqual(raw_text_url(DOCUMENT), DOCUMENT['raw_text_url'])
        self.assertEqual(raw_text_url({**DOCUMENT, 'raw_text_url': None}), DOCUMENT['raw_text_url'])

    def test_rejects_host_or_doc_mismatch(self):
        for bad in (
            'https://evil.example/documents/full_text/text/2024/03/27/2024-06419.txt',
            'http://www.federalregister.gov/documents/full_text/text/2024/03/27/2024-06419.txt',
            'https://www.federalregister.gov/documents/full_text/text/2024/03/27/2024-11111.txt',
            'https://www.federalregister.gov/documents/full_text/text/2024/03/27/2024-06419.txt?x=1',
            'https://www.federalregister.gov/documents/full_text/text/2024/03/26/2024-06419.txt',
        ):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                raw_text_url({**DOCUMENT, 'raw_text_url': bad})

    def test_reject_public_inspection_source(self):
        with self.assertRaises(ValueError):
            raw_text_url({**DOCUMENT, 'source': 'public_inspection'})

    def test_sections_and_matching(self):
        spans = applicability_spans(DOCUMENT_BODY.decode())
        self.assertEqual(len(spans), 1)
        output = screen_full_text(DOCUMENT_BODY.decode(), 'PW1100G')
        self.assertEqual(output['total_model_mentions'], 1)
        self.assertEqual(output['mentions_in_candidate_applicability_section'], 1)
        self.assertFalse(output['asset_applicability_verified'])
        self.assertTrue(output['review_required'])

    def test_nonmatching_model_is_not_a_clearance(self):
        result = screen_full_text(DOCUMENT_BODY.decode(), 'LEAP-1A')
        self.assertIn('not_clearance', result['screening_result'])
        self.assertEqual(result['total_model_mentions'], 0)

    def test_full_text_elsewhere_not_applicability(self):
        result = screen_full_text('Intro mentions PW1100G.\n(c) Applicability\nOnly other models.\n(d) Subject\nEngine.', 'PW1100G')
        self.assertIn('elsewhere', result['screening_result'])
        self.assertEqual(result['mentions_in_candidate_applicability_section'], 0)

    def test_series_variant_candidates_in_applicability(self):
        # Reflects the structure of the operative (c) section in AD 2024-05-11.
        body = ("SUMMARY: Applies to some PW1100G series engines.\n"
                "(c) Applicability\n"
                "This AD applies to engines Model PW1122G-JM, PW1127G1A-JM, PW1133GA-JM, "
                "and PW1428G-JM equipped with specified parts.\n"
                "(d) Subject\n Engine.\n")
        result = screen_full_text(body, 'PW1100G')
        self.assertEqual(result['mentions_in_candidate_applicability_section'], 0)
        self.assertEqual(result['family_variant_candidate_count'], 3)
        self.assertEqual([x['candidate_variant'] for x in result['family_variant_candidates']],
                         ['PW1122G-JM', 'PW1127G1A-JM', 'PW1133GA-JM'])
        self.assertEqual(result['screening_result'],
                         'series_variant_candidates_in_applicability_review_required')
        self.assertFalse(result['asset_applicability_verified'])

    def test_family_separation_pw1400g_and_no_outside_matches(self):
        body = ("Discussion of PW1127G-JM.\n"
                "(c) Applicability\n"
                "Engine Model PW1428G-JM with listed parts.\n"
                "(d) Subject\n"
                "Comment from operators of PW1130G-JM engines.\n")
        r11 = screen_full_text(body, 'PW1100G')
        r14 = screen_full_text(body, 'PW1400G')
        self.assertEqual(r11['family_variant_candidate_count'], 0)
        self.assertEqual(r14['family_variant_candidate_count'], 1)
        self.assertEqual(r14['family_variant_candidates'][0]['candidate_variant'], 'PW1428G-JM')

    def test_other_families_not_assumed_mapped(self):
        body = ('(c) Applicability\nApplies to PW1127G-JM\n(d) Subject\n')
        result = screen_full_text(body, 'CFM56')
        self.assertEqual(result['family_variant_candidate_count'], 0)
        self.assertEqual(result['family_variant_matching_basis'],
                         'no series-to-variant heuristic configured')
        self.assertIn('not_clearance', result['screening_result'])

    def test_no_detected_applicability_heading_remains_unverified(self):
        body = 'SUMMARY: PW1100G engines. Report on PW1127G-JM engines.'
        result = screen_full_text(body, 'PW1100G')
        self.assertEqual(result['family_variant_candidate_count'], 0)
        self.assertEqual(result['applicability_headings_identified'], 0)
        self.assertTrue(result['review_required'])

    def test_run_saves_evidence_and_database_unchanged(self):
        attempts=[]
        result = run(self.db, '2024-06419', 'PW1100G', self.evidence_dir,
                     as_of='2026-10-20', fetcher=lambda url: attempts.append(url) or DOCUMENT_BODY,
                     now=lambda: '2026-10-20T20:20:00+00:00')
        self.assertEqual(attempts, [DOCUMENT['raw_text_url']])
        self.assertEqual(result['evidence_state'], 'new_full_text_hash_stored')
        self.assertEqual(result['sha256'], hashlib.sha256(DOCUMENT_BODY).hexdigest())
        self.assertEqual(Path(result['evidence_text_path']).read_bytes(), DOCUMENT_BODY)
        manifest=json.loads(Path(result['evidence_manifest_path']).read_text())
        self.assertEqual(manifest['source_url'], DOCUMENT['raw_text_url'])
        self.assertEqual(self.db.read_bytes(), self.original_bytes)

    def test_second_same_text_does_not_duplicate(self):
        a = run(self.db, '2024-06419', 'PW1100G', self.evidence_dir,
                fetcher=lambda _: DOCUMENT_BODY)
        b = run(self.db, '2024-06419', 'PW1100G', self.evidence_dir,
                fetcher=lambda _: DOCUMENT_BODY)
        self.assertEqual(a['sha256'], b['sha256'])
        self.assertEqual(b['evidence_state'], 'identical_full_text_hash_seen_before')
        self.assertEqual(len(list(self.evidence_dir.rglob('*.txt'))), 1)

    def test_changed_text_preserved_as_separate_hash(self):
        run(self.db, '2024-06419', 'PW1100G', self.evidence_dir,
            fetcher=lambda _: DOCUMENT_BODY)
        changed=run(self.db, '2024-06419', 'PW1100G', self.evidence_dir,
                    fetcher=lambda _: DOCUMENT_BODY+b'\nSource correction line.')
        self.assertEqual(changed['evidence_state'], 'new_full_text_hash_stored')
        self.assertEqual(len(list(self.evidence_dir.rglob('*.txt'))), 2)

    def test_offline_reuses_evidence_without_network(self):
        run(self.db, '2024-06419', 'PW1100G', self.evidence_dir,
            fetcher=lambda _: DOCUMENT_BODY)
        result=run(self.db, '2024-06419', 'PW1100G', self.evidence_dir, offline=True,
                   fetcher=lambda _: self.fail('Should never access network'))
        self.assertEqual(result['evidence_state'], 'cached_offline_not_rechecked_against_source')
        self.assertEqual(result['total_model_mentions'], 1)

    def test_offline_detects_tamper(self):
        result=run(self.db, '2024-06419', 'PW1100G', self.evidence_dir,
                   fetcher=lambda _: DOCUMENT_BODY)
        Path(result['evidence_text_path']).write_bytes(b'tampered')
        with self.assertRaises(ValueError):
            run(self.db, '2024-06419', 'PW1100G', self.evidence_dir, offline=True)

    def test_missing_db_document(self):
        with self.assertRaises(ValueError):
            read_published_snapshot(self.db, '2024-12345')

    def test_download_blocks_untrusted_url_without_network(self):
        with self.assertRaises(ValueError):
            download_text('https://example.com/payload.txt')

    def test_oversized_simulated_response_rejected(self):
        from src.aerocie.full_text_review import MAX_TEXT_BYTES
        with self.assertRaises(ValueError):
            run(self.db, '2024-06419', 'PW1100G', self.evidence_dir,
                fetcher=lambda _: b'a' * (MAX_TEXT_BYTES+1))

    def test_no_interaction_with_nonpublished_record(self):
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.execute('DELETE FROM document_snapshots')
            conn.execute('INSERT INTO document_snapshots(source, document_number, payload_json) VALUES (?, ?, ?)',
                         ('public_inspection', '2024-06419', json.dumps({**DOCUMENT,'source':'public_inspection'})))
        with self.assertRaisesRegex(ValueError, 'No locally collected PUBLISHED'):
            run(self.db, '2024-06419', 'PW1100G', self.evidence_dir, offline=True)


if __name__ == '__main__':
    unittest.main()
