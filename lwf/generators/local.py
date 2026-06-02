"""Local generator — capability+config → Hermes runner"""

from ..parser import topo_sort


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
        f'BRIDGE_DIR = os.path.expanduser(f"~/.lwf/bridges/{repo_dir}/{path}")',
        '',
        'def pull():',
        '    repo_dir = os.path.dirname(BRIDGE_DIR)',
        '    if not os.path.exists(repo_dir):',
        f'        subprocess.run(["git", "clone", "git@github.com:{repo}.git", repo_dir])',
        '    subprocess.run(["git", "-C", repo_dir, "pull"])',
        '',
        'def run():',
        '    pull()',
        '    print(f"[lwf] {name}")',
        '',
    ]

    for s in ordered:
        sid = s['id']
        cap = s['capability']
        using = s.get('using', '')
        cfg = s.get('config', {})

        lines.append(f'def task_{sid}():')
        lines.append(f'    """{cap}/{using}"""')

        if cap == 'consume' and using == 'obsidian':
            vault = cfg.get('vault_path', '~/notebook')
            folder = cfg.get('folder', '')
            data_file = cfg.get('data_file', '')
            lines.append(f'    data_path = os.path.join(BRIDGE_DIR, "{data_file}")')
            lines.append('    if os.path.exists(data_path):')
            lines.append(f'        vault = os.path.expanduser("{vault}")')
            lines.append(f'        target = os.path.join(vault, "{folder}")')
            lines.append('        os.makedirs(target, exist_ok=True)')
            lines.append('        print(f"[lwf] {sid}: 数据就绪 → {target}")')
            lines.append('    else:')
            lines.append('        print(f"[lwf] {sid}: 无新数据")')
        else:
            lines.append(f'    print(f"[lwf] {sid}: {cap}/{using} — 需子项目实现")')

        lines.append('')

    lines.append("if __name__ == '__main__':")
    lines.append('    run()')
    for s in ordered:
        lines.append(f'    task_{s["id"]}()')

    return '\n'.join(lines)
