"""Local generator — capability+config → Hermes runner"""

from ..parser import topo_sort


def _render_task(step):
    """Render a single local task. Each step decides its own idle logic."""
    sid = step['id']
    cap = step['capability']
    using = step.get('using', '')
    cfg = step.get('config', {})
    is_optional = step.get('optional', False)

    lines = [f'def task_{sid}():']
    lines.append(f'    """{sid} · {cap}/{using}"""')

    if cap == 'consume' and using == 'script':
        script = cfg.get('file', '')
        data_file = cfg.get('data_file', '')
        if data_file:
            lines.append(f'    data_path = os.path.join(BRIDGE_DIR, "{data_file}")')
            lines.append('    if os.path.exists(data_path) and os.path.getsize(data_path) > 0:')
            lines.append(f'        print(f"  [lwf] {sid}: 数据就绪，运行 {script}")')
            lines.append(f'        rc = subprocess.run(["python3", "{script}"], cwd=WORK_DIR)')
            lines.append(f'        if rc.returncode != 0:')
            lines.append(f'            print(f"  ! {sid} 失败 ({{rc.returncode}})" )')
            lines.append('    else:')
            if is_optional:
                lines.append(f'        print(f"  [lwf] {sid}: optional — 无数据，跳过")')
            else:
                lines.append(f'        print(f"  [lwf] {sid}: idle — 等待数据")')
        else:
            # 无 data_file 约束，总是执行
            lines.append(f'    rc = subprocess.run(["python3", "{script}"], cwd=WORK_DIR)')
            lines.append(f'    if rc.returncode != 0:')
            lines.append(f'        print(f"  ! {sid} 失败 ({{rc.returncode}})" )')

    elif cap == 'notify' and using == 'hermes':
        """Hermes 通知 — stdout 被 Hermes cron 捕获后送微信/邮箱"""
        message = cfg.get('message', 'LWF 通知')
        lines.append(f'    print("{message}")')
        lines.append('    print("  ✓ notify: hermes 已捕获通知")')

    else:
        # 未知 capability：data_file 感知 idle
        data_file = cfg.get('data_file', '')
        if data_file:
            lines.append(f'    data_path = os.path.join(BRIDGE_DIR, "{data_file}")')
            lines.append('    if os.path.exists(data_path) and os.path.getsize(data_path) > 0:')
            lines.append(f'        print(f"  [lwf] {sid}: {cap}/{using} — data 就绪")')
            lines.append('    else:')
            if is_optional:
                lines.append(f'        print(f"  [lwf] {sid}: optional — 无数据，跳过")')
            else:
                lines.append(f'        print(f"  [lwf] {sid}: idle — 等待数据")')
        else:
            lines.append(f'    print(f"  [lwf] {sid}: {cap}/{using} — 需子项目实现")')

    lines.append('')
    return '\n'.join(lines)


def generate_local(name, local_steps, bridge_info):
    ordered = topo_sort(local_steps)
    repo = bridge_info.get('repo', '')
    path = bridge_info.get('path', '')
    repo_dir = repo.replace('/', '_')

    # 判断是否需要桥仓库：有步骤配置了 data_file 就需要
    needs_bridge = any(
        'data_file' in step.get('config', {})
        for step in local_steps
    )

    lines = [
        '#!/usr/bin/env python3',
        f'"""LWF Local Runner — {name}"""',
        'import json, os, subprocess',
        '',
        'WORK_DIR = os.getcwd()',
        '',
    ]

    if needs_bridge:
        lines.append(f'BRIDGE_DIR = os.path.expanduser(f"~/.lwf/bridges/{repo_dir}/{path}")')
        lines.append('')
        lines.append('def pull():')
        lines.append('    repo_dir = os.path.dirname(BRIDGE_DIR)')
        lines.append('    if not os.path.exists(repo_dir):')
        lines.append(f'        subprocess.run(["git", "clone", "git@github.com:{repo}.git", repo_dir])')
        lines.append('    subprocess.run(["git", "-C", repo_dir, "pull"])')
        lines.append('')

    lines.append('def run():')
    lines.append(f'    print(f"  [lwf] {name}: 开始")')
    lines.append('')

    for s in ordered:
        lines.append(_render_task(s))

    lines.append('')
    lines.append("if __name__ == '__main__':")
    if needs_bridge:
        lines.append('    pull()')
    lines.append('    run()')
    for s in ordered:
        lines.append(f'    task_{s["id"]}()')

    return '\n'.join(lines)
