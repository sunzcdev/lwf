"""YAML parser + validator"""

import json, sys
from pathlib import Path
import yaml
from jsonschema import Draft7Validator
from .schema import WORKFLOW_SCHEMA

def load(path):
    path = Path(path)
    with open(path, encoding='utf-8') as f:
        return yaml.safe_load(f)

def validate(data):
    errors = sorted(Draft7Validator(WORKFLOW_SCHEMA).iter_errors(data), key=lambda e: e.path)
    if errors:
        for e in errors:
            p = ' → '.join(str(x) for x in e.path) or 'root'
            print(f"  ❌ {p}: {e.message}")
        sys.exit(1)
    ids = {s['id'] for s in data['steps']}
    for s in data['steps']:
        for d in s.get('depends', []):
            if d not in ids:
                print(f"  ❌ {s['id']}.depends: 不存在的步骤 '{d}'")
                sys.exit(1)
    return True

def classify(steps):
    gha = [s for s in steps if s['runner'] == 'gha']
    local = [s for s in steps if s['runner'] == 'local']
    return gha, local

def topo_sort(steps):
    step_map = {s['id']: s for s in steps}
    visited, result = set(), []
    def visit(sid, path):
        if sid in path:
            print(f"  ❌ 依赖循环: {' → '.join(path + [sid])}")
            sys.exit(1)
        if sid in visited:
            return
        path.append(sid)
        visited.add(sid)
        for d in step_map[sid].get('depends', []):
            if d in step_map:
                visit(d, path)
        path.pop()
        result.append(step_map[sid])
    for s in steps:
        if s['id'] not in visited:
            visit(s['id'], [])
    return result
