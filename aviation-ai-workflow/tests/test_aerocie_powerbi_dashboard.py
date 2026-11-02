"""Phase 28 report contract and synthetic relational semantics, not Desktop rendering."""
from __future__ import annotations
from collections import Counter
from contextlib import closing
from decimal import Decimal
import csv
import importlib.util
import json
from pathlib import Path
import re
import sqlite3
from tempfile import TemporaryDirectory
import unittest

from src.aerocie import underwriting_pipeline as pipeline
from src.aerocie.export_reconciliation import reconcile

ROOT = Path(__file__).resolve().parents[1]
POWERBI = ROOT / 'powerbi'
REPORT = POWERBI / 'AeroCIE-Underwriting.Report'
PAGES = REPORT / 'definition/pages'
MODEL = POWERBI / 'AeroCIE-Underwriting.SemanticModel/definition'
SPEC = importlib.util.spec_from_file_location('validate_powerbi', ROOT / 'scripts/validate_powerbi.py')
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)
EXPECTED = ['Overview', 'RiskAnalysis', 'MROSeverity', 'EvidenceIntegrity']


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def visuals(page):
    return [read(p) for p in sorted((PAGES / page / 'visuals').glob('*/visual.json'))]


def fields(obj):
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in {'Column', 'Measure'}:
                yield key, value['Expression']['SourceRef']['Entity'], value['Property']
            else:
                yield from fields(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from fields(value)


class DashboardDefinitionTests(unittest.TestCase):
    def test_every_project_json_validates_against_offline_microsoft_schemas(self):
        result = VALIDATOR.validate_project()
        self.assertEqual(result['status'], 'PASS')
        self.assertGreaterEqual(result['json_files_validated'], 74)
        self.assertFalse(result['desktop_runtime_verified'])

    def test_schema_validator_rejects_malformed_container(self):
        with TemporaryDirectory() as folder:
            project = Path(folder)
            sample = visuals('Overview')[0]
            sample['position']['width'] = 'not a number'
            (project / 'visual.json').write_text(json.dumps(sample), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'not a number'):
                VALIDATOR.validate_project(project)

    def test_four_visible_pages_have_navigation_and_populated_visuals(self):
        metadata = read(PAGES / 'pages.json')
        self.assertEqual(metadata['pageOrder'], EXPECTED)
        self.assertEqual(metadata['activePageName'], 'Overview')
        self.assertEqual({p.name for p in PAGES.iterdir() if p.is_dir()}, set(EXPECTED))
        for page in EXPECTED:
            data = read(PAGES / page / 'page.json')
            items = visuals(page)
            self.assertNotEqual(data.get('visibility'), 'HiddenInViewMode')
            self.assertGreaterEqual(len(items), 10)
            self.assertEqual(sum(v['visual']['visualType'] == 'pageNavigator' for v in items), 1)
            self.assertGreaterEqual(sum('query' in v['visual'] for v in items), 6)
            self.assertIn('INTERNAL_DEMO_ONLY', json.dumps(items))
            self.assertIn('UNDERWRITER_REVIEW_REQUIRED', json.dumps(items))

    def test_visuals_fit_canvas_without_overlap_and_interactions_resolve(self):
        for page in EXPECTED:
            data = read(PAGES / page / 'page.json')
            items = visuals(page)
            names = {v['name'] for v in items}
            self.assertEqual(len(names), len(items))
            for i, item in enumerate(items):
                a = item['position']
                self.assertGreater(a['width'], 0)
                self.assertGreater(a['height'], 0)
                self.assertGreaterEqual(a['x'], 0)
                self.assertGreaterEqual(a['y'], 0)
                self.assertLessEqual(a['x'] + a['width'], data['width'])
                self.assertLessEqual(a['y'] + a['height'], data['height'])
                for other in items[i + 1:]:
                    b = other['position']
                    overlap = (a['x'] < b['x'] + b['width'] and b['x'] < a['x'] + a['width'] and
                               a['y'] < b['y'] + b['height'] and b['y'] < a['y'] + a['height'])
                    self.assertFalse(overlap, (page, item['name'], other['name']))
            for interaction in data['visualInteractions']:
                self.assertIn(interaction['source'], names)
                self.assertIn(interaction['target'], names)
                self.assertEqual(interaction['type'], 'DataFilter')

    def test_every_field_binding_resolves_to_existing_model_and_native_role(self):
        model = {}
        for path in (MODEL / 'tables').glob('*.tmdl'):
            text = path.read_text(encoding='utf-8')
            model[path.stem] = {
                'Column': set(re.findall(r'^\tcolumn (\w+)', text, re.M)),
                'Measure': set(a or b for a, b in re.findall(r"^\tmeasure (?:'([^']+)'|(\w+)) =", text, re.M)),
            }
        allowed = {'card': {'Values'}, 'multiRowCard': {'Values'}, 'tableEx': {'Values'},
                   'slicer': {'Values'}, 'clusteredBarChart': {'Category', 'Y'},
                   'clusteredColumnChart': {'Category', 'Y'}}
        for page in EXPECTED:
            for item in visuals(page):
                visual = item['visual']
                if 'query' not in visual:
                    continue
                state = visual['query']['queryState']
                self.assertEqual(set(state), allowed[visual['visualType']])
                for role in state.values():
                    refs = [p['queryRef'] for p in role['projections']]
                    self.assertTrue(refs)
                    self.assertEqual(len(refs), len(set(refs)))
                    for projection in role['projections']:
                        found = list(fields(projection))
                        self.assertEqual(len(found), 1)
                        kind, table, field = found[0]
                        self.assertIn(field, model[table][kind], (page, item['name'], table, field))
                        self.assertEqual(projection['queryRef'], f'{table}.{field}')
                if visual['visualType'] == 'card':
                    self.assertEqual(next(fields(visual))[0], 'Measure')

    def test_overview_six_kpis_are_model_measures_and_no_benchmark_literals(self):
        items = visuals('Overview')
        kpis = [v for v in items if v['name'].startswith('kpi_')]
        self.assertEqual(len(kpis), 6)
        self.assertEqual({f for v in kpis for _, _, f in fields(v)}, {
            'Synthetic Submissions', 'Selected Advisory Quote', 'Selected Advisory Refer', 'Selected Advisory Decline',
            'Missing Evidence', 'Requested Hull Total Not Insured'})
        for page in EXPECTED:
            for value in ('34045000', '34,045,000', '46243', '46,243', '104080', '104,080', '208159', '208,159'):
                self.assertNotIn(value, json.dumps(visuals(page)))

    def test_theme_and_project_links_resolve(self):
        report = read(REPORT / 'definition/report.json')
        custom = report['themeCollection']['customTheme']
        self.assertEqual(custom['type'], 'RegisteredResources')
        item = report['resourcePackages'][0]['items'][0]
        self.assertEqual(item['name'], custom['name'])
        theme = read(REPORT / 'StaticResources/RegisteredResources' / item['path'])
        self.assertEqual(theme['dataColors'][:2], ['#10263F', '#168FA6'])
        self.assertEqual(theme['textClasses']['title']['fontFace'], 'Montserrat')
        entry = read(POWERBI / 'AeroCIE-Underwriting.pbip')
        self.assertTrue((POWERBI / entry['artifacts'][0]['report']['path']).is_dir())
        link = read(REPORT / 'definition.pbir')['datasetReference']['byPath']['path']
        self.assertEqual((REPORT / link).resolve(), MODEL.parent.resolve())
        self.assertIn('AeroCIEDataFolder', (MODEL / 'expressions.tmdl').read_text())

    def test_dax_references_and_expression_delimiters_are_consistent(self):
        # Structural guard only. This is deliberately not described as a DAX parser.
        texts = {p.stem: p.read_text() for p in (MODEL / 'tables').glob('*.tmdl')}
        columns = {t: set(re.findall(r"^\tcolumn (\w+)", text, re.M)) for t, text in texts.items()}
        names = [a or b for text in texts.values()
                 for a, b in re.findall(r"^\tmeasure (?:'([^']+)'|(\w+)) =", text, re.M)]
        self.assertEqual(len(names), len(set(names)))
        for table, text in texts.items():
            expressions = re.findall(r"^\tmeasure [^=]+ =(.*?)(?=^\t(?:measure|column|partition) |\Z)", text, re.M | re.S)
            for expression in expressions:
                dax = expression.split('\n\t\tformatString:')[0]
                for target, field in re.findall(r"'([^']+)'\[([^]]+)\]", dax):
                    self.assertIn(field, columns[target], (table, target, field))
                without_columns = re.sub(r"'[^']+'\[[^]]+\]", '', dax)
                for name in re.findall(r"\[([^]]+)\]", without_columns):
                    self.assertIn(name, names, (table, name))
                # DAX quoted text can contain punctuation; remove it before balancing.
                tokens = re.sub(r'"(?:[^"\n]|"")*"', '', dax)
                balance = 0
                for char in tokens:
                    balance += (char == '(') - (char == ')')
                    self.assertGreaterEqual(balance, 0, (table, dax))
                self.assertEqual(balance, 0, (table, dax))

    def test_relationships_only_link_proven_submission_grain_snapshots(self):
        text = (MODEL / 'relationships.tmdl').read_text()
        blocks = re.split(r'(?m)^relationship ', text)[1:]
        self.assertEqual(len(blocks), 3)
        children = set()
        for block in blocks:
            self.assertIn('fromCardinality: one', block)
            self.assertIn('toCardinality: one', block)
            self.assertIn('crossFilteringBehavior: bothDirections', block)
            self.assertIn('toColumn: v_submission_triage.submission_id', block)
            child = re.search(r'fromColumn: (\w+)\.submission_id', block).group(1)
            children.add(child)
        self.assertEqual(children, {'v_submission_features', 'v_severity_scenarios', 'submission_quality'})
        # Acyclic hub; no manufacturer/model or source-registry fanout relationship.
        self.assertNotIn('source_registry.', text)
        self.assertNotIn('.model', text)

    def test_case_slicers_filter_every_case_visual(self):
        for page in EXPECTED:
            items = visuals(page)
            links = {(i['source'], i['target']) for i in read(PAGES / page / 'page.json')['visualInteractions']}
            registry = {'source_registry', 'import_checks', 'evidence_kpi_2', 'evidence_kpi_3'}
            targets = {v['name'] for v in items if 'query' in v['visual']} - registry
            for slicer in (v for v in items if v['visual']['visualType'] == 'slicer'):
                for target in targets - {slicer['name']}:
                    self.assertIn((slicer['name'], target), links)

    def test_report_advisory_measures_intersect_instead_of_replacing_label_filters(self):
        text = (MODEL / 'tables/v_submission_triage.tmdl').read_text()
        for label in ('Quote', 'Refer', 'Decline'):
            expression = re.search(r"^\tmeasure 'Selected Advisory " + label + r"' = (.+)$", text, re.M).group(1)
            self.assertIn('KEEPFILTERS(', expression)
            self.assertIn('COALESCE(', expression)
            self.assertIn(f'[triage_recommendation] = "{label}"', expression)
        self.assertIn('VAR _Refer = [Selected Advisory Refer]', text)

    def test_mro_and_quality_tables_expose_inputs_and_reasons(self):
        mro = {f for v in visuals('MROSeverity') for _, _, f in fields(v)}
        self.assertTrue({'mro_severity_days', 'mro_cost_pressure_index', 'mean_parts_availability',
                         'scenario_low_usd', 'scenario_base_usd', 'scenario_high_usd'}.issubset(mro))
        evidence = {f for v in visuals('EvidenceIntegrity') for _, _, f in fields(v)}
        self.assertTrue({'quality_status', 'issue_codes', 'payload_sha256', 'license_status', 'retrieved_at'}.issubset(evidence))


class DashboardSyntheticDataTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.db = self.root / 'synthetic.db'
        self.exports = self.root / 'exports'
        pipeline.create_db(self.db)
        pipeline.export_tables(self.db, self.exports)

    def rows(self, table):
        with (self.exports / (table + '.csv')).open(encoding='utf-8-sig', newline='') as handle:
            return list(csv.DictReader(handle))

    def test_fresh_exports_meet_all_acceptance_benchmarks(self):
        result = reconcile(self.exports)
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['submission_count'], 7)
        self.assertEqual(result['labels'], {'Quote': 2, 'Refer': 4, 'Decline': 1})
        self.assertEqual(Decimal(result['requested_hull_total_usd_NOT_INSURED_VALUE']), Decimal('34045000'))
        self.assertEqual(list(map(Decimal, result['scenario_totals_usd_NOT_CLAIM_FORECAST'])), list(map(Decimal, ['46243', '104080', '208159'])))
        self.assertEqual(result['files_verified_by_sha256'], 10)
        self.assertFalse(result['release_authorized'])
        missing = [r for r in self.rows('v_submission_triage') if r['insufficient_evidence'] == '1']
        self.assertEqual(len(missing), 2)
        self.assertTrue(all(r['triage_recommendation'] == 'Refer' and not r['risk_points'] for r in missing))

    def test_one_to_one_relationship_keys_are_complete_unique_and_no_hull_fanout(self):
        triage = self.rows('v_submission_triage')
        ids = {r['submission_id'] for r in triage}
        for table in ('v_submission_features', 'v_severity_scenarios', 'submission_quality'):
            rows = self.rows(table)
            self.assertEqual(len(rows), len(ids))
            self.assertEqual({r['submission_id'] for r in rows}, ids)
        with closing(sqlite3.connect(self.db)) as con:
            row = con.execute('''SELECT count(*),sum(t.requested_hull_value_usd)
                FROM v_submission_triage t JOIN v_submission_features f USING(submission_id)
                JOIN v_severity_scenarios s USING(submission_id)''').fetchone()
        self.assertEqual(row, (7, 34045000))

    def test_filter_contract_preserves_selected_ids_scenarios_and_blank_evidence(self):
        # This tests relational semantics of declared joins, not execution of DAX by Desktop.
        triage = self.rows('v_submission_triage')
        severity = {r['submission_id']: r for r in self.rows('v_severity_scenarios')}
        quality = {r['submission_id']: r for r in self.rows('submission_quality')}
        for field in ('submission_id', 'model', 'operation_type', 'triage_recommendation'):
            partitions = Counter()
            for selected in {r[field] for r in triage}:
                rows = [r for r in triage if r[field] == selected]
                for row in rows:
                    sid = row['submission_id']
                    self.assertEqual(severity[sid]['triage_recommendation'], row['triage_recommendation'])
                    self.assertEqual(quality[sid]['research_label'], row['triage_recommendation'])
                    if row['insufficient_evidence'] == '1':
                        self.assertFalse(severity[sid]['scenario_base_usd'])
                    partitions[sid] += 1
            self.assertEqual(set(partitions.values()), {1})
