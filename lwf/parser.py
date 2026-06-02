"""YAML 解析 + 校验模块"""

import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("[lwf] 需要 PyYAML: pip install PyYAML", file=sys.stderr)
    sys.exit(1)

from jsonschema import validate, ValidationError
try:
    from jsonschema import Draft7Validator
except ImportError:
    print("[lwf] 需要 jsonschema: pip install jsonschema", file=sys.stderr)
    sys.exit(1)

from .schema import WORKFLOW_SCHEMA


def load(path):
    """加载 YAML 文件"""
    path = Path(path)
    if not path.exists():
        print(f"[lwf] 文件不存在: {path}", file=sys.stderr)
        sys.exit(1)
    with open(path, encoding='utf-8') as f:
        return yaml.safe_load(f)


def validate_workflow(data):
    """校验工作流定义"""
    validator = Draft7Validator(WORKFLOW_SCHEMA)
    errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
    if errors:
        for e in errors:
            path = ' → '.join(str(p) for p in e.path) if e.path else 'root'
            print(f"  ❌ {path}: {e.message}", file=sys.stderr)
        sys.exit(1)

    # 额外校验：depends 引用必须存在
    step_ids = {s['id'] for s in data['steps']}
    for s in data['steps']:
        for dep in s.get('depends', []):
            if dep not in step_ids:
                print(f"  ❌ steps → {s['id']}.depends: 引用了不存在的步骤 '{dep}'", file=sys.stderr)
                sys.exit(1)

    # 校验：local runner 必须有 trigger（除非依赖链有触发源）
    all_local_ids = {s['id'] for s in data['steps'] if s['runner'] == 'local'}
    for s in data['steps']:
        if s['runner'] != 'local':
            continue
        if s.get('trigger'):
            continue
        # 检查依赖链：所有依赖都是 local 且有人有 trigger 就行
        def _has_trigger_source(sid, visited):
            if sid in visited:
                return False
            visited.add(sid)
            step = {ss['id']: ss for ss in data['steps']}.get(sid)
            if not step:
                return False
            if step.get('trigger'):
                return True
            for dep in step.get('depends', []):
                if dep in all_local_ids and _has_trigger_source(dep, visited):
                    return True
            return False
        has_source = _has_trigger_source(s['id'], set())
        if not has_source:
            print(f"  ❌ steps → {s['id']}: local runner 必须指定 trigger，或依赖一个有 trigger 的 local 步骤", file=sys.stderr)
            sys.exit(1)

    return True


def parse(path):
    """加载 + 校验 + 返回结构化数据"""
    data = load(path)
    validate_workflow(data)
    return data


def classify_steps(steps):
    """按 runner 分类步骤"""
    gha_steps = [s for s in steps if s['runner'] == 'gha']
    local_steps = [s for s in steps if s['runner'] == 'local']
    return gha_steps, local_steps


def build_dag(steps):
    """构建依赖 DAG，返回拓扑排序后的步骤列表"""
    step_map = {s['id']: s for s in steps}
    visited = set()
    result = []

    def visit(sid, path):
        if sid in path:
            cycle = ' → '.join(path + [sid])
            print(f"  ❌ 依赖循环检测: {cycle}", file=sys.stderr)
            sys.exit(1)
        if sid in visited:
            return
        path.append(sid)
        visited.add(sid)
        for dep in step_map[sid].get('depends', []):
            if dep in step_map:  # 只算同组内的依赖
                visit(dep, path)
        path.pop()
        result.append(step_map[sid])

    for s in steps:
        if s['id'] not in visited:
            visit(s['id'], [])

    return result
