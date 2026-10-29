"""AeroCIE-018: loopback-only synthetic research workbench.

Renders intake, builds the reviewed Phase 21 preview, and returns HTML/JSON
artifacts to the browser. All report generation is read-only and in memory.
"""
from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from typing import Callable
from urllib.parse import urlsplit

from . import customer_report, pilot_report
from .review_journal import _packet

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web" / "aerocie-workbench"
DEFAULT_PACKET = ROOT / "sample-data" / "phase20" / "packet.json"
DEFAULT_INTAKE = ROOT / "sample-data" / "phase20" / "intake.json"
MAX_REQUEST_BYTES = 8192
SCHEMA = "AEROCIE-018-LOCAL-WORKBENCH-v1"


class RequestError(ValueError):
    """Bad synthetic intake or blocked browser request."""


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    obj: dict = {}
    for key, value in pairs:
        if key in obj:
            raise RequestError("Duplicate JSON keys are not allowed")
        obj[key] = value
    return obj


def build_bundle(intake: dict, packet_path: Path = DEFAULT_PACKET) -> dict:
    """Create two synchronized research outputs from synthetic case data.

    The temporary intake is never retained and research databases are not opened.
    """
    valid = customer_report.validate_intake(intake)
    if not packet_path.is_file():
        raise ValueError("Synthetic evidence packet unavailable")
    with TemporaryDirectory(prefix="aerocie-workbench-") as tmp:
        intake_file = Path(tmp) / "intake.json"
        intake_file.write_text(json.dumps(valid, sort_keys=True, ensure_ascii=False), encoding="utf-8")
        model = pilot_report.make_model(intake_file, packet_path)
        structured = customer_report.build_report(intake_file, packet_path)
        html = pilot_report.render_html(model)
    if (model["external_release_authorized"] is not False
            or structured["external_release_authorized"] is not False):
        raise ValueError("External release guard refused")
    return {
        "schema": SCHEMA,
        "case_id": valid["case_id"],
        "release": "HOLD_FOR_HUMAN_REVIEW",
        "external_release_authorized": False,
        "metrics": model["counts"],
        "report_html": html,
        "report_json": structured,
    }


def _fixture(packet_path: Path, intake_path: Path) -> dict:
    intake = customer_report.validate_intake(
        json.loads(intake_path.read_text(encoding="utf-8-sig"), object_pairs_hook=_unique_object))
    packet = _packet(packet_path)
    if packet["research_candidate"]["subject_id"] != intake["subject_id"]:
        raise ValueError("Synthetic fixture subject mismatch")
    return {
        "schema": SCHEMA,
        "intake": intake,
        "publication_count": len(packet["published_metadata_documents"]),
        "candidate_status": packet["review_disposition"],
    }


class WorkbenchHandler(BaseHTTPRequestHandler):
    """Private browser handler. Never bind this handler to a public interface."""

    # Supplied by create_server(), which sets the packet and fixture paths.
    packet_path = DEFAULT_PACKET
    intake_path = DEFAULT_INTAKE
    server_version = "AeroCIE-Workbench/1"
    sys_version = ""

    def log_message(self, format: str, *args: object) -> None:
        # Avoid writing intake or request details to access logs.
        return

    def _trusted_host(self) -> bool:
        host = self.headers.get("Host", "")
        port = self.server.server_address[1]
        return host in {f"127.0.0.1:{port}", f"localhost:{port}"}

    def _valid_origin(self) -> bool:
        origin = self.headers.get("Origin")
        if origin is None:
            return True
        port = self.server.server_address[1]
        return origin in {f"http://127.0.0.1:{port}", f"http://localhost:{port}"}

    def _send(self, status: int, data: bytes, media: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", media)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Content-Security-Policy",
                         "default-src 'none'; script-src 'self'; "
                         "style-src 'self' 'unsafe-inline'; connect-src 'self'; "
                         "img-src 'self' data:; frame-src blob:; "
                         "object-src 'none'; base-uri 'none'; form-action 'self'")
        self.end_headers()
        self.wfile.write(data)

    def _json(self, status: int, data: dict) -> None:
        self._send(status, json.dumps(data, ensure_ascii=False).encode("utf-8"),
                   "application/json; charset=utf-8")

    def do_GET(self) -> None:
        if not self._trusted_host():
            return self._json(403, {"error": "Unrecognized local hostname"})
        path = urlsplit(self.path).path
        resources = {
            "/": ("index.html", "text/html; charset=utf-8"),
            "/assets/app.css": ("app.css", "text/css; charset=utf-8"),
            "/assets/app.js": ("app.js", "text/javascript; charset=utf-8"),
        }
        if path in resources:
            file_name, media = resources[path]
            return self._send(200, (WEB / file_name).read_bytes(), media)
        if path == "/api/fixture":
            try:
                return self._json(200, _fixture(self.packet_path, self.intake_path))
            except (ValueError, KeyError, OSError, TypeError):
                return self._json(503, {"error": "Synthetic fixture failed integrity checks"})
        if path == "/api/health":
            return self._json(200, {"status": "ok", "schema": SCHEMA,
                                    "bind": "loopback", "data_mode": "synthetic"})
        return self._json(404, {"error": "Resource not found"})

    def do_POST(self) -> None:
        if not self._trusted_host() or not self._valid_origin():
            return self._json(403, {"error": "Browser origin refused"})
        if urlsplit(self.path).path != "/api/report":
            return self._json(404, {"error": "Resource not found"})
        if self.headers.get("Content-Type", "").split(";")[0].strip().lower() != "application/json":
            return self._json(415, {"error": "JSON required"})
        try:
            size = int(self.headers.get("Content-Length", ""))
        except ValueError:
            size = -1
        if not 0 < size <= MAX_REQUEST_BYTES:
            return self._json(413, {"error": "Payload size refused"})
        try:
            raw = self.rfile.read(size)
            payload = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
            if not isinstance(payload, dict) or set(payload) != {"intake"}:
                raise RequestError("Request requires exactly one intake object")
            result = build_bundle(payload["intake"], self.packet_path)
        except (UnicodeDecodeError, json.JSONDecodeError, RequestError, ValueError, TypeError, KeyError):
            return self._json(422, {"error": "Synthetic intake or evidence validation failed"})
        except OSError:
            return self._json(503, {"error": "Local evidence unavailable"})
        return self._json(200, result)

    def do_OPTIONS(self) -> None:
        self._json(405, {"error": "Cross-origin requests are disabled"})


def create_server(*, packet: Path = DEFAULT_PACKET, intake: Path = DEFAULT_INTAKE,
                  port: int = 8092) -> ThreadingHTTPServer:
    if type(port) is not int or not (0 <= port <= 65535):
        raise ValueError("Invalid local port")
    class Handler(WorkbenchHandler):
        packet_path = packet
        intake_path = intake
    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AeroCIE synthetic local pilot workbench")
    parser.add_argument("--port", type=int, default=8092)
    # Paths permit tests and other reviewed synthetic fixtures, not customer intake.
    parser.add_argument("--packet", type=Path, default=DEFAULT_PACKET)
    args = parser.parse_args(argv)
    try:
        server = create_server(packet=args.packet, port=args.port)
    except (ValueError, OSError) as exc:
        print("Workbench could not start:", exc, file=sys.stderr)
        return 1
    addr, bound_port = server.server_address
    print(f"AeroCIE synthetic workbench: http://{addr}:{bound_port}/", flush=True)
    print("Use Ctrl+C to stop. No real customer data or external publication allowed.", flush=True)
    try:
        server.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
