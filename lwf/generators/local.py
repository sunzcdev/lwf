"""Local generator — 为本地 Hermes 生成 watch 配置"""

from ..parser import build_dag


def _generate_local_script(step, bridge_info):
    """生成 Hermes 本地可执行的步骤代码"""
    t = step['action']['type']
    sid = step['id']

    if t == 'obsidian':
        template = step['action'].get('template', '')
        data_ref = step['action'].get('data', '')
        return (
            f'def task_{sid}():\n'
            f'    """写入 Obsidian 日记"""\n'
            f'    import json, os\n'
            f'    data_path = os.path.join(BRIDGE_DIR, "{data_ref}")\n'
            f'    if os.path.exists(data_path):\n'
            f'        with open(data_path) as f:\n'
            f'            data = json.load(f)\n'
            f'        print(f"[lwf] {sid}: 数据已就绪")\n'
            f'    else:\n'
            f'        print(f"[lwf] {sid}: 数据文件不存在 {{data_path}}")\n'
        )

    elif t == 'wechat':
        content = step['action'].get('content', '')
        return (
            f'def task_{sid}():\n'
            f'    """推送微信通知"""\n'
            f'    msg = """{content}"""\n'
            f'    print(f"[lwf] {sid}: wechat push: {{msg[:50]}}...")\n'
        )

    elif t == 'gha-trigger':
        workflow = step['action']['workflow']
        inputs = step['action'].get('inputs', {})
        flags = ' '.join(f'-f {k}="{v}"' for k, v in inputs.items())
        return (
            f'def task_{sid}():\n'
            f'    """触发新一轮 GHA"""\n'
            f'    import subprocess\n'
            f'    cmd = ["gh", "workflow", "run", "{workflow}"]\n'
            f'    if "{flags}".strip():\n'
            f'        cmd.extend("{flags}".split())\n'
            f'    subprocess.run(cmd, check=True)\n'
            f'    print(f"[lwf] {sid}: 已触发 {workflow}")\n'
        )

    else:
        return (
            f'def task_{sid}():\n'
            f'    print(f"[lwf] {sid}: 未知 action 类型 {t}")\n'
        )


def generate_local_runner(workflow, local_steps, bridge_info):
    """生成本地 runner Python 脚本"""
    ordered = build_dag(local_steps)
    bridge_repo = bridge_info.get('repo', '')
    bridge_path = bridge_info.get('path', '')

    repo_dir_name = bridge_repo.replace('/', '_')

    lines = [
        '#!/usr/bin/env python3',
        '"""LWF Local Runner — 由 lwf deploy 自动生成"""',
        '',
        'import json, os, subprocess, sys',
        'from pathlib import Path',
        '',
        f'WORKFLOW = "{workflow}"',
        f'BRIDGE_REPO = "{bridge_repo}"',
        f'BRIDGE_PATH = "{bridge_path}"',
        f'BRIDGE_DIR = os.path.expanduser(f"~/.lwf/bridges/{repo_dir_name}/{bridge_path}")',
        '',
        '',
        'def pull_bridge():',
        '    """拉取桥仓库最新数据"""',
        '    repo_dir = os.path.dirname(BRIDGE_DIR)',
        '    if not os.path.exists(repo_dir):',
        '        os.makedirs(repo_dir, exist_ok=True)',
        f'        subprocess.run(["git", "clone", "git@github.com:{bridge_repo}.git", repo_dir], check=True)',
        '    subprocess.run(["git", "-C", repo_dir, "pull"], check=True)',
        '',
        '',
        'def run():',
        '    pull_bridge()',
        '    print(f"[lwf] 运行工作流: {WORKFLOW}")',
        '',
    ]

    for s in ordered:
        lines.append('')
        lines.append(_generate_local_script(s, bridge_info))
        lines.append('')

    lines.append('')
    lines.append('if __name__ == "__main__":')
    lines.append('    run()')
    lines.append('    # 按依赖顺序执行本地任务')
    for s in ordered:
        lines.append(f'    task_{s["id"]}()')

    return '\n'.join(lines)


def generate_watch_config(workflow, local_steps, bridge_info):
    """为 Hermes 生成 watch 配置描述"""
    tasks_summary = []
    for s in local_steps:
        tasks_summary.append(f'  - {s["id"]}: {s["action"]["type"]} (trigger: {s.get("trigger", "manual")})')

    return (
        f'LWF 本地 runner 工作流: {workflow}\n'
        f'桥仓库: {bridge_info.get("repo", "N/A")}\n'
        f'本地步骤:\n' + '\n'.join(tasks_summary)
    )
