"""AeroCIE-018: local UI and browser report workflow end-to-end tests."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import threading
from tempfile import TemporaryDirectory
import unittest
from urllib import error, request

from src.aerocie import customer_report, workbench


class WorkbenchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = TemporaryDirectory()
        cls.base = Path(cls.tmp.name)
        fixture = Path(__file__).resolve().parents[1] / "sample-data" / "phase20"
        cls.intake_path = cls.base / "intake.json"
        cls.packet_path = cls.base / "packet.json"
        shutil.copyfile(fixture / "intake.json", cls.intake_path)
        shutil.copyfile(fixture / "packet.json", cls.packet_path)
        cls.intake = json.loads(cls.intake_path.read_text())
        cls.initial_packet_hash = hashlib.sha256(cls.packet_path.read_bytes()).hexdigest()
        cls.initial_intake_hash = hashlib.sha256(cls.intake_path.read_bytes()).hexdigest()
        cls.server = workbench.create_server(packet=cls.packet_path, intake=cls.intake_path, port=0)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        cls.tmp.cleanup()

    def api(self, path, *, method="GET", payload=None, headers=None, raw=None):
        url = f"http://127.0.0.1:{self.port}{path}"
        body = raw if raw is not None else (json.dumps(payload).encode() if payload is not None else None)
        hdr = dict(headers or {})
        if method == "POST" and "Content-Type" not in hdr:
            hdr["Content-Type"] = "application/json"
        req = request.Request(url, data=body, headers=hdr, method=method)
        try:
            with request.urlopen(req, timeout=8) as resp:
                return resp.status, dict(resp.headers), resp.read()
        except error.HTTPError as exc:
            return exc.code, dict(exc.headers), exc.read()

    def test_health_loopback(self):
        code, headers, body = self.api("/api/health")
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(body)["data_mode"], "synthetic")
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertIn("script-src 'self'", headers["Content-Security-Policy"])
        self.assertNotIn("Access-Control-Allow-Origin", headers)

    def test_assets_have_local_uris_and_no_external_tracking(self):
        for path, mime in (("/", "text/html"), ("/assets/app.js", "text/javascript"),
                           ("/assets/app.css", "text/css")):
            with self.subTest(path=path):
                code, headers, body = self.api(path)
                self.assertEqual(code, 200)
                self.assertIn(mime, headers["Content-Type"])
                self.assertGreater(len(body), 200)
                self.assertNotIn(b"https://cdn", body)
        code, _, body = self.api("/")
        self.assertIn(b'iframe id="report-frame"', body)
        self.assertIn(b'form id="intake-form"', body)
        self.assertIn(b"Download JSON", body)

    def test_fixture_is_synthetic_and_consistent(self):
        code, _, body = self.api("/api/fixture")
        self.assertEqual(code, 200)
        fixture = json.loads(body)
        self.assertTrue(fixture["intake"]["synthetic"])
        self.assertEqual(fixture["candidate_status"], "HOLD_FOR_HUMAN_REVIEW")
        self.assertEqual(fixture["publication_count"], 1)

    def test_complete_browser_report_workflow(self):
        code, _, body = self.api("/api/report", method="POST", payload={"intake": self.intake})
        self.assertEqual(code, 200, body[:120])
        result = json.loads(body)
        self.assertEqual(result["schema"], workbench.SCHEMA)
        self.assertFalse(result["external_release_authorized"])
        self.assertEqual(result["release"], "HOLD_FOR_HUMAN_REVIEW")
        self.assertEqual(result["metrics"]["documents"], 1)
        self.assertEqual(result["metrics"]["unresolved_review_checks"], 8)
        self.assertIn("Aviation Regulatory", result["report_html"])
        self.assertIn("NOT FOR CLIENT RELEASE", result["report_html"])
        self.assertEqual(result["report_json"]["intake"], self.intake)
        self.assertNotIn("href=\"https://www.federalregister.gov/documents/2000", result["report_html"])
        self.assertEqual(result["report_json"]["evidence"]["documents"][0]["url"], None)
        self.assertEqual(self.initial_packet_hash, hashlib.sha256(self.packet_path.read_bytes()).hexdigest())
        self.assertEqual(self.initial_intake_hash, hashlib.sha256(self.intake_path.read_bytes()).hexdigest())

    def test_edited_synthetic_question_reflected_in_artifacts(self):
        item = dict(self.intake, requested_scope="Synthetic question about correction history")
        code, _, body = self.api("/api/report", method="POST", payload={"intake": item})
        self.assertEqual(code, 200)
        result = json.loads(body)
        self.assertIn(item["requested_scope"], result["report_html"])
        self.assertEqual(result["report_json"]["intake"]["requested_scope"], item["requested_scope"])
        self.assertFalse(result["report_json"]["external_release_authorized"])

    def test_untrusted_text_is_escaped_in_html(self):
        item = dict(self.intake, requested_scope='<script>fetch("evil")</script>')
        code, _, body = self.api("/api/report", method="POST", payload={"intake": item})
        self.assertEqual(code, 200)
        html = json.loads(body)["report_html"]
        self.assertNotIn('<script>fetch("evil")</script>', html)
        self.assertIn('&lt;script&gt;', html)

    def test_unknown_personal_data_field_refused(self):
        item = dict(self.intake, email="pilot@example.com")
        code, _, body = self.api("/api/report", method="POST", payload={"intake": item})
        self.assertEqual(code, 422)
        self.assertNotIn(b"pilot@example.com", body)

    def test_real_customer_flag_refused(self):
        for change in ({"synthetic": False}, {"organization": "Real Aviation Inc"},
                       {"subject_id": "demo:another-subject"}):
            with self.subTest(change=change):
                item = dict(self.intake, **change)
                code, _, _ = self.api("/api/report", method="POST", payload={"intake": item})
                self.assertEqual(code, 422)

    def test_invalid_json_and_duplicate_fields(self):
        samples = [b"not-json", b'{"intake": {}, "intake": {}}', b"[]", b"{}"]
        for sample in samples:
            with self.subTest(sample=sample):
                code, _, _ = self.api("/api/report", method="POST", raw=sample)
                self.assertEqual(code, 422)

    def test_max_payload_limit(self):
        code, _, _ = self.api("/api/report", method="POST", raw=b"x" * (workbench.MAX_REQUEST_BYTES + 1))
        self.assertEqual(code, 413)

    def test_invalid_content_type_refused(self):
        code, _, _ = self.api("/api/report", method="POST", payload={"intake": self.intake},
                              headers={"Content-Type": "text/plain"})
        self.assertEqual(code, 415)

    def test_cross_origin_refused(self):
        code, _, _ = self.api("/api/report", method="POST", payload={"intake": self.intake},
                              headers={"Origin": "https://malicious.example"})
        self.assertEqual(code, 403)
        code, _, _ = self.api("/api/report", method="POST", payload={"intake": self.intake},
                              headers={"Origin": f"http://127.0.0.1:{self.port}"})
        self.assertEqual(code, 200)
        code, _, _ = self.api("/api/report", method="OPTIONS")
        self.assertEqual(code, 405)

    def test_dns_rebinding_hostname_refused(self):
        code, _, _ = self.api("/api/fixture", headers={"Host": "attacker.example"})
        self.assertEqual(code, 403)
        code, _, _ = self.api("/api/report", method="POST", payload={"intake": self.intake},
                              headers={"Host": "attacker.example"})
        self.assertEqual(code, 403)

    def test_no_path_traversal_or_upload_endpoints(self):
        for path in ("/api/db", "/download/sqlite3", "/assets/secrets.txt", "/api/report/../fixture"):
            with self.subTest(path=path):
                code, _, _ = self.api(path)
                self.assertEqual(code, 404)
        code, _, _ = self.api("/api/other", method="POST", payload={"intake": self.intake})
        self.assertEqual(code, 404)

    def test_invalid_packet_does_not_render_or_modify(self):
        with TemporaryDirectory() as tmp:
            packet = Path(tmp) / "packet.json"
            original = self.packet_path.read_bytes()
            packet.write_bytes(original.replace(b"Synthetic aviation", b"Altered aviation"))
            with self.assertRaises(ValueError):
                workbench.build_bundle(self.intake, packet)
            self.assertTrue(packet.is_file())
            self.assertEqual(packet.read_bytes(), original.replace(b"Synthetic aviation", b"Altered aviation"))

    def test_bundle_does_not_create_case_folder(self):
        before = {x.name for x in self.base.iterdir()}
        bundle = workbench.build_bundle(self.intake, self.packet_path)
        self.assertEqual(bundle["release"], "HOLD_FOR_HUMAN_REVIEW")
        self.assertEqual(before, {x.name for x in self.base.iterdir()})

    def test_invalid_port_refused(self):
        for port in (-1, 65536, "8092", True):
            with self.subTest(port=port):
                with self.assertRaises(ValueError):
                    workbench.create_server(port=port)

    def test_customer_report_schema_unchanged(self):
        self.assertEqual(workbench.SCHEMA, "AEROCIE-018-LOCAL-WORKBENCH-v1")
        self.assertEqual(self.intake["schema"], customer_report.SCHEMA)


if __name__ == "__main__":
    unittest.main()
