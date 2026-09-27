"""Loopback-only demonstration server; not a production hosting service."""
import argparse
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import sqlite3
from urllib.parse import parse_qs, urlsplit

from zipsmart import ROOT, STATES, lookup_zip, read_metrics


class Handler(BaseHTTPRequestHandler):
    def __init__(self, *args, directory, **kwargs):
        self.directory = Path(directory)
        super().__init__(*args, **kwargs)

    def respond(self, status, value, content_type='application/json; charset=utf-8'):
        body = (json.dumps(value) if content_type.startswith('application/json') else value).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlsplit(self.path)
        query = parse_qs(parsed.query, keep_blank_values=True)
        database = self.directory / 'zipsmart.sqlite'
        try:
            if parsed.path in ('/', '/dashboard.html'):
                return self.respond(200, (self.directory / 'dashboard.html').read_text(encoding='utf-8'), 'text/html; charset=utf-8')
            if parsed.path == '/api/health':
                return self.respond(200, {'status': 'ok', 'record_count': len(read_metrics(database)), 'data_type': 'synthetic'})
            if parsed.path == '/api/zips':
                if set(query) - {'state'} or any(len(v) != 1 for v in query.values()):
                    return self.respond(400, {'error': 'Use only one optional state parameter.'})
                state = query.get('state', [None])[0]
                if state is not None and state not in STATES:
                    return self.respond(400, {'error': 'state must be an uppercase two-letter US state code.'})
                rows = read_metrics(database, state)
                return self.respond(200, {'data_type': 'synthetic', 'count': len(rows), 'records': rows})
            if parsed.path == '/api/zip':
                codes = query.get('zip', [])
                if set(query) != {'zip'} or len(codes) != 1 or not re.fullmatch(r'[0-9]{5}', codes[0]):
                    return self.respond(400, {'error': 'Provide exactly one five-digit zip parameter.'})
                row = lookup_zip(database, codes[0])
                return self.respond(200, row) if row else self.respond(404, {'error': 'ZIP absent from synthetic sample.'})
            return self.respond(404, {'error': 'Endpoint not found.'})
        except (OSError, sqlite3.Error):
            return self.respond(503, {'error': 'Demo data unavailable. Run python zipsmart.py first.'})


def make_server(directory, port=8000):
    return ThreadingHTTPServer(('127.0.0.1', port), partial(Handler, directory=directory))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=ROOT / 'build')
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    with make_server(args.directory, args.port) as server:
        print(f'Demo dashboard: http://127.0.0.1:{server.server_port}', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
