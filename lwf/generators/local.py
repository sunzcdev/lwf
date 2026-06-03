"""Local generator — capability+config → Hermes runner"""

from ..parser import topo_sort


def _render_task(step):
    """Render a single local task with idle/no-op support."""
    sid = step['id']
    cap = step['capability']
    using = step.get('using', '')
    cfg = step.get('config', {})
    is_optional = step.get('optional', False)

    lines = [f'def task_{sid}():']
    lines.append(f'    """{sid} · {cap}/{using}"""')

    idle_check = (
        "    if not data_exists():"
        "        print(f'  [lwf] {sid}: idle — 无数据')"
        "        return"
    )

    if cap == 'consume' and using == 'obsidian':
        vault = cfg.get('vault_path', '~/notebook')
        folder = cfg.get('folder', '')
        data_file = cfg.get('data_file', '')
        lines.append(f'    data_path = os.path.join(BRIDGE_DIR, "{data_file}")')
        lines.append('    if os.path.exists(data_path) and os.path.getsize(data_path) > 0:')
        lines.append(f'        vault = os.path.expanduser("{vault}")')
        lines.append(f'        target = os.path.join(vault, "{folder}")')
        lines.append('        os.makedirs(target, exist_ok=True)')
        lines.append('        print(f"  [lwf] {sid}: 数据就绪 → {target}")')
        lines.append('    else:')
        lines.append('        print(f"  [lwf] {sid}: idle — 无新数据")')

    elif cap == 'consume' and using == 'script':
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
            lines.append(f'        print(f"  [lwf] {sid}: idle — 无新数据")')
        else:
            # 无 data_file 约束，直接执行
            lines.append(f'    rc = subprocess.run(["python3", "{script}"], cwd=WORK_DIR)')
            lines.append(f'    if rc.returncode != 0:')
            lines.append(f'        print(f"  ! {sid} 失败 ({{rc.returncode}})" )')

    elif cap == 'consume' and using == 'rclone':
        """rclone sync — 直写坚果云等云存储"""
        remote = cfg.get('remote', '')
        source = cfg.get('source', '')
        target = cfg.get('target', '')
        data_file = cfg.get('data_file', '')
        if data_file:
            lines.append(f'    data_path = os.path.join(BRIDGE_DIR, "{data_file}")')
            lines.append('    if os.path.exists(data_path) and os.path.getsize(data_path) > 0:')
            lines.append(f'        print(f"  [lwf] {sid}: rclone {source} → {remote}:{target}")')
            lines.append(f'        rc = subprocess.run(["rclone", "copy", "{source}", "{remote}:{target}"])')
            lines.append(f'        if rc.returncode != 0:')
            lines.append(f'            print(f"  ! rclone 失败 ({{rc.returncode}})" )')
            lines.append('    else:')
            lines.append(f'        print(f"  [lwf] {sid}: idle — 无新数据")')
        else:
            lines.append(f'    rc = subprocess.run(["rclone", "copy", "{source}", "{remote}:{target}"])')
            lines.append(f'    if rc.returncode != 0:')
            lines.append(f'        print(f"  ! rclone 失败 ({{rc.returncode}})" )')

    else:
        # 未知 capability：data_file 感知 idle
        data_file = cfg.get('data_file', '')
        if data_file:
            lines.append(f'    data_path = os.path.join(BRIDGE_DIR, "{data_file}")')
            lines.append('    if os.path.exists(data_path) and os.path.getsize(data_path) > 0:')
            lines.append(f'        print(f"  [lwf] {sid}: {cap}/{using} — data 就绪")')
            lines.append('    else:')
            lines.append(f'        print(f"  [lwf] {sid}: idle — 无数据")')
        else:
            lines.append(f'    print(f"  [lwf] {sid}: {cap}/{using} — 需子项目实现")')

    lines.append('')
    return '\n'.join(lines)


def generate_local(name, local_steps, bridge_info):
    ordered = topo_sort(local_steps)
    repo = bridge_info.get('repo', '')
    path = bridge_info.get('path', '')
    repo_dir = repo.replace('/', '_')

    lines = [
        '#!/usr/bin/env python3',
        f'"""LWF Local Runner — {name}"""',
        'import json, os, subprocess',
        '',
        'WORK_DIR = os.getcwd()',
        '',
        f'BRIDGE_DIR = os.path.expanduser(f"~/.lwf/bridges/{repo_dir}/{path}")',
        '',
        '# ── data existence check (idle detection) ──',
        'def data_exists():',
        '    """全局数据探测：bridge 目录下有非空文件即有数据"""',
        '    if not os.path.exists(BRIDGE_DIR):',
        '        return False',
        '    for root, dirs, files in os.walk(BRIDGE_DIR):',
        '        for f in files:',
        '            fp = os.path.join(root, f)',
        '            if os.path.getsize(fp) > 0:',
        '                return True',
        '    return False',
        '',
        'def pull():',
        '    repo_dir = os.path.dirname(BRIDGE_DIR)',
        '    if not os.path.exists(repo_dir):',
        f'        subprocess.run(["git", "clone", "git@github.com:{repo}.git", repo_dir])',
        '    subprocess.run(["git", "-C", repo_dir, "pull"])',
        '',
        'def run():',
        '    if not data_exists():',
        '        print(f"  [lwf] {name}: idle — 无数据，跳过所有任务")',
        '        return',
        '    print(f"  [lwf] {name}: 数据就绪，开始处理")',
        '',
    ]

    for s in ordered:
        lines.append(_render_task(s))

    lines.append('')
    lines.append("if __name__ == '__main__':")
    lines.append('    pull()')
    lines.append('    run()')
    for s in ordered:
        lines.append(f'    task_{s["id"]}()')

    return '\n'.join(lines)
