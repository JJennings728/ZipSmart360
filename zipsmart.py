"""Reproducible, standard-library-only ZIPSmart portfolio demonstration."""
import argparse
import csv
import html
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import tempfile

ROOT = Path(__file__).resolve().parent
FIELDS = ('zip_code', 'state', 'population', 'households',
          'median_household_income', 'unemployment_pct', 'data_year', 'data_type')
STATES = set('AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN '
             'MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY'.split())


def validate_csv(path):
    """Validate the complete input before creating or replacing any database."""
    rows, seen = [], set()
    with Path(path).open(newline='', encoding='utf-8-sig') as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != list(FIELDS):
            raise ValueError('CSV headers must exactly match: ' + ','.join(FIELDS))
        for line, raw in enumerate(reader, 2):
            try:
                if None in raw or any(v is None or not v.strip() for v in raw.values()):
                    raise ValueError('missing or extra field')
                row = {k: v.strip() for k, v in raw.items()}
                if not re.fullmatch(r'[0-9]{5}', row['zip_code']):
                    raise ValueError('ZIP must be five digits, including leading zeros')
                if row['zip_code'] in seen:
                    raise ValueError('duplicate ZIP')
                if row['state'] not in STATES:
                    raise ValueError('unsupported state code')
                if row['data_type'] != 'synthetic':
                    raise ValueError('this demo accepts synthetic data only')
                for key in ('population', 'households', 'data_year'):
                    row[key] = int(row[key])
                for key in ('median_household_income', 'unemployment_pct'):
                    row[key] = float(row[key])
                    if not math.isfinite(row[key]):
                        raise ValueError(key + ' must be finite')
                if row['population'] < 0 or not 0 <= row['households'] <= row['population']:
                    raise ValueError('invalid population or household count')
                if row['median_household_income'] < 0 or not 0 <= row['unemployment_pct'] <= 100:
                    raise ValueError('invalid income or unemployment percentage')
                if not 1900 <= row['data_year'] <= 2100:
                    raise ValueError('invalid data year')
                seen.add(row['zip_code'])
                rows.append(row)
            except (ValueError, TypeError) as exc:
                raise ValueError(f'CSV line {line}: {exc}') from exc
    if not rows:
        raise ValueError('CSV must contain at least one data row')
    if len({r['data_year'] for r in rows}) != 1:
        raise ValueError('all rows must use the same data year')
    return rows


def connect_readonly(path):
    connection = sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def read_metrics(database, state=None):
    connection = connect_readonly(database)
    try:
        sql = 'SELECT * FROM zip_metrics'
        params = ()
        if state is not None:
            sql += ' WHERE state = ?'
            params = (state,)
        return [dict(row) for row in connection.execute(sql + ' ORDER BY zip_code', params)]
    finally:
        connection.close()


def lookup_zip(database, zip_code):
    connection = connect_readonly(database)
    try:
        row = connection.execute('SELECT * FROM zip_metrics WHERE zip_code = ?', (zip_code,)).fetchone()
        return dict(row) if row else None
    finally:
        connection.close()


def render_dashboard(rows):
    template = (ROOT / 'web' / 'dashboard.html').read_text(encoding='utf-8')
    body = ''.join(
        '<tr>' + ''.join(f'<td>{html.escape(str(value))}</td>' for value in (
            r['zip_code'], r['state'], f"{r['population']:,}", f"{r['households']:,}",
            f"${r['median_household_income']:,.0f}", f"{r['unemployment_pct']:.1f}%")) + '</tr>'
        for r in rows)
    options = ''.join(f'<option>{html.escape(s)}</option>' for s in sorted({r['state'] for r in rows}))
    return (template.replace('{{ROWS}}', body).replace('{{STATES}}', options)
            .replace('{{COUNT}}', str(len(rows)))
            .replace('{{POPULATION}}', f"{sum(r['population'] for r in rows):,}")
            .replace('{{YEAR}}', str(rows[0]['data_year'])))


def build(source, output):
    rows = validate_csv(source)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(suffix='.sqlite', dir=output)
    os.close(fd)
    connection = None
    try:
        connection = sqlite3.connect(temporary)
        connection.row_factory = sqlite3.Row
        connection.executescript((ROOT / 'sql/schema.sql').read_text())
        connection.executemany('INSERT INTO zip_metrics VALUES (?,?,?,?,?,?,?,?)',
                               [tuple(r[k] for k in FIELDS) for r in rows])
        connection.commit()
        summary = [dict(r) for r in connection.execute((ROOT / 'sql/state_summary.sql').read_text())]
        connection.close()
        connection = None
        os.replace(temporary, output / 'zipsmart.sqlite')
    finally:
        if connection is not None:
            connection.close()
        Path(temporary).unlink(missing_ok=True)
    ordered = read_metrics(output / 'zipsmart.sqlite')
    report = {'data_type': 'synthetic', 'data_year': rows[0]['data_year'],
              'record_count': len(rows), 'duplicate_zip_count': 0,
              'checks': ['required fields', 'ZIP format and uniqueness', 'state codes',
                         'finite numeric ranges', 'consistent year', 'synthetic label'],
              'limitations': 'Format validation does not verify actual ZIP geography or real-world accuracy.'}
    for name, content in [('state_summary.json', summary), ('quality_report.json', report),
                          ('zip_metrics.json', ordered)]:
        (output / name).write_text(json.dumps(content, indent=2) + '\n', encoding='utf-8')
    with (output / 'zip_metrics.csv').open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(ordered)
    (output / 'dashboard.html').write_text(render_dashboard(ordered), encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=ROOT / 'data/sample_zip_data.csv')
    parser.add_argument('--output', type=Path, default=ROOT / 'build')
    args = parser.parse_args()
    try:
        report = build(args.input, args.output)
    except (ValueError, OSError, sqlite3.Error) as exc:
        parser.exit(1, f'Build failed: {exc}\n')
    print(f"Validated {report['record_count']} synthetic ZIP rows. Dashboard: {args.output / 'dashboard.html'}")


if __name__ == '__main__':
    main()
