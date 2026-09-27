import csv
import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import urlopen

from server import make_server
from zipsmart import ROOT, FIELDS, build, lookup_zip, validate_csv


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name) / 'build'
        self.source = ROOT / 'data/sample_zip_data.csv'

    def altered_input(self, mutate):
        with self.source.open(newline='') as handle:
            rows = list(csv.DictReader(handle))
        mutate(rows)
        source = Path(self.temp.name) / 'altered.csv'
        with source.open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        return source

    def test_build_and_sql_totals(self):
        report = build(self.source, self.output)
        self.assertEqual(report['record_count'], 12)
        self.assertEqual(lookup_zip(self.output / 'zipsmart.sqlite', '00501')['zip_code'], '00501')
        summary = json.loads((self.output / 'state_summary.json').read_text())
        iowa = next(row for row in summary if row['state'] == 'IA')
        self.assertEqual(iowa['sample_zip_count'], 3)
        self.assertEqual(iowa['sample_population'], 35700)
        self.assertEqual(iowa['mean_of_zip_income_medians'], 60000)
        dashboard = (self.output / 'dashboard.html').read_text()
        self.assertIn('Synthetic data only', dashboard)
        self.assertIn('<td>00501</td>', dashboard)
        self.assertNotIn('{{', dashboard)

    def test_repeatable_text_outputs(self):
        build(self.source, self.output)
        before = {p.name: p.read_bytes() for p in self.output.iterdir() if p.suffix != '.sqlite'}
        build(self.source, self.output)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.output.iterdir() if p.suffix != '.sqlite'})

    def test_invalid_input_does_not_replace_database(self):
        build(self.source, self.output)
        before = (self.output / 'zipsmart.sqlite').read_bytes()
        invalid = self.altered_input(lambda rows: rows.append(dict(rows[0])))
        with self.assertRaisesRegex(ValueError, 'duplicate ZIP'):
            build(invalid, self.output)
        self.assertEqual(before, (self.output / 'zipsmart.sqlite').read_bytes())

    def test_bad_values_rejected(self):
        for field, value in [('zip_code', '501'), ('state', 'XX'), ('population', '-1'),
                             ('households', '999999'), ('median_household_income', 'NaN'),
                             ('unemployment_pct', 'Infinity'), ('unemployment_pct', '101'),
                             ('data_type', 'real'), ('data_year', '2024')]:
            with self.subTest(field=field, value=value):
                source = self.altered_input(lambda rows: rows[0].update({field: value}))
                with self.assertRaises(ValueError):
                    validate_csv(source)

    def test_empty_and_bad_header_rejected(self):
        source = Path(self.temp.name) / 'empty.csv'
        for content in ['', ','.join(FIELDS) + '\n', 'zip,state\n00501,NY\n']:
            source.write_text(content)
            with self.assertRaises(ValueError):
                validate_csv(source)

    def test_query_parameterization(self):
        build(self.source, self.output)
        self.assertIsNone(lookup_zip(self.output / 'zipsmart.sqlite', "' OR 1=1 --"))

    def test_http_contract(self):
        build(self.source, self.output)
        server = make_server(self.output, 0)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        base = f'http://127.0.0.1:{server.server_port}'
        try:
            with urlopen(base + '/api/zip?zip=00501', timeout=5) as response:
                self.assertEqual(json.load(response)['zip_code'], '00501')
            with urlopen(base + '/api/zips?state=IA', timeout=5) as response:
                self.assertEqual(json.load(response)['count'], 3)
            with urlopen(base + '/api/health', timeout=5) as response:
                self.assertEqual(json.load(response)['record_count'], 12)
            with urlopen(base + '/', timeout=5) as response:
                self.assertIn(b'Synthetic data only', response.read())
            for path, status in [('/api/zip?zip=501', 400), ('/api/zip?zip=99999', 404),
                                 ('/api/zip?zip=00501&zip=10001', 400),
                                 ('/api/zips?state=XX', 400), ('/api/zips?other=x', 400),
                                 ('/missing', 404), ('/../../README.md', 404)]:
                with self.subTest(path=path), self.assertRaises(HTTPError) as error:
                    urlopen(base + path, timeout=5)
                self.assertEqual(error.exception.code, status)
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=5)


if __name__ == '__main__':
    unittest.main()
