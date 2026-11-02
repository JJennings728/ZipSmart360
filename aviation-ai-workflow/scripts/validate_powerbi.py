"""Offline Microsoft JSON-schema validation; does not execute DAX or Desktop.

The schemas in tests/powerbi_schemas are unmodified Microsoft definitions.
No network lookup is permitted: a missing referenced schema fails validation.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from jsonschema import Draft7Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT7

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / 'tests' / 'powerbi_schemas'
PROJECT = ROOT / 'powerbi'
BASE = 'https://developer.microsoft.com/json-schemas/'


def registry() -> Registry:
    result = Registry()
    for path in SCHEMAS.rglob('*.json'):
        if path.name == 'manifest.json':
            continue
        data = json.loads(path.read_text(encoding='utf-8'))
        uri = BASE + path.relative_to(SCHEMAS).as_posix()
        result = result.with_resource(uri, Resource.from_contents(data, default_specification=DRAFT7))
    return result


def validate_project(project: Path = PROJECT) -> dict:
    manifest = json.loads((SCHEMAS / 'manifest.json').read_text(encoding='utf-8'))
    for name, metadata in manifest.items():
        digest = hashlib.sha256((SCHEMAS / name).read_bytes()).hexdigest()
        if digest != metadata['sha256']:
            raise ValueError(f'Schema checksum mismatch: {name}')
    reg = registry()
    count = 0
    for path in sorted(project.rglob('*')):
        if not path.is_file() or path.suffix not in {'.json', '.pbip', '.pbir', '.pbism'}:
            continue
        data = json.loads(path.read_text(encoding='utf-8'))
        uri = data.get('$schema')
        if path.name == 'SRP_AeroCIE.json':
            uri = BASE + 'reportThemeSchema-2.152.json'
        if not uri:
            raise ValueError(f'No declared schema: {path}')
        schema = reg.contents(uri)
        errors = sorted(Draft7Validator(schema, registry=reg).iter_errors(data), key=lambda e: str(e.path))
        if errors:
            raise ValueError(f'{path.relative_to(project)}: ' + '\n'.join(f'{list(e.path)}: {e.message}' for e in errors))
        count += 1
    return {'status': 'PASS', 'json_files_validated': count, 'schema_files_verified': len(manifest), 'desktop_runtime_verified': False}


if __name__ == '__main__':
    print(json.dumps(validate_project(), indent=2))
