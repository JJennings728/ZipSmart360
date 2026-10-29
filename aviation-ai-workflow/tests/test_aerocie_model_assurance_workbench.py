"""Phase 23 browser API integration tests for the research-only model record."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import threading
import unittest
from urllib import request, error

from src.aerocie import workbench


class ModelAssuranceRouteTests(unittest.TestCase):
    def setUp(self):
        self.server = workbench.create_server(port=0)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=4)

    def get(self, path, headers=None):
        req = request.Request(f'http://127.0.0.1:{self.port}{path}', headers=headers or {})
        try:
            with request.urlopen(req, timeout=5) as resp:
                return resp.status, resp.read()
        except error.HTTPError as e:
            return e.code, e.read()

    def test_model_assurance_endpoint_has_transparent_fail_reasons(self):
        code, content = self.get('/api/model-assurance')
        self.assertEqual(code, 200)
        data = json.loads(content)
        self.assertFalse(data['external_release_authorized'])
        self.assertEqual(data['metrics']['count'], 24)
        self.assertEqual(data['research_quality_gate'], 'REVIEW_REQUIRED')
        self.assertIn('INSUFFICIENT_INDEPENDENT_EVALUATION_ROWS', data['reasons'])
        self.assertRegex(data['input_sha256'], r'^[0-9a-f]{64}$')

    def test_bad_host_rejected(self):
        code, _ = self.get('/api/model-assurance', {'Host': 'attacker.example'})
        self.assertEqual(code, 403)

    def test_invalid_model_fixture_is_reported_unavailable(self):
        with TemporaryDirectory() as d:
            file = Path(d) / 'eval.json'
            file.write_text('{"synthetic":false}')
            self.server.RequestHandlerClass.model_path = file
            code, content = self.get('/api/model-assurance')
            self.assertEqual(code, 503)
            self.assertNotIn(b'"synthetic":false', content)

    def test_browser_exposes_downloadable_record(self):
        code, html = self.get('/')
        self.assertEqual(code, 200)
        self.assertIn(b'AI assurance record', html)
        self.assertIn(b'download-assurance', html)
        code, js = self.get('/assets/app.js')
        self.assertEqual(code, 200)
        self.assertIn(b'/api/model-assurance', js)
