"""LWF CLI — Lightweight Workflow Framework 命令行工具"""

import argparse
import sys
import os
from pathlib import Path

from .parser import parse, classify_steps
from .generators.gha import generate as generate_gha
from .generators.local import generate_local_runner, generate_watch_config


def cmd_validate(args):
    """校验 YAML 文件"""
    data = parse(args.workflow)
    gha_steps, local_steps = classify_steps(data['steps'])
    print(f"✅ {args.workflow.name} 校验通过")
    print(f"   GHA 步骤: {len(gha_steps)}")
    print(f"   Local 步骤: {len(local_steps)}")
    if data.get('bridge'):
        print(f"   数据桥: {data['bridge']['type']} → {data['bridge'].get('repo', 'N/A')}")


def cmd_deploy(args):
    """部署工作流：生成 GHA .yml + 本地 runner"""
    data = parse(args.workflow)
    workflow_name = data['name']
    gha_steps, local_steps = classify_steps(data['steps'])

    out_dir = args.out or Path.cwd()
    out_dir = Path(out_dir)

    # 1. 生成 GHA workflow（如果存在 GHA 步骤）
    if gha_steps:
        trigger_schedule = data.get('trigger', {}).get('schedule')
        gha_yml = generate_gha(
            workflow_name, gha_steps,
            trigger_schedule=trigger_schedule
        )
        gha_dir = out_dir / '.github' / 'workflows'
        gha_dir.mkdir(parents=True, exist_ok=True)
        gha_path = gha_dir / f'{workflow_name}.yml'
        gha_path.write_text(gha_yml, encoding='utf-8')
        print(f"  📄 GHA: {gha_path}")

    # 2. 生成本地 runner（如果存在 local 步骤）
    if local_steps:
        bridge_info = data.get('bridge', {})
        local_script = generate_local_runner(workflow_name, local_steps, bridge_info)
        local_dir = out_dir / 'lwf' / 'runners'
        local_dir.mkdir(parents=True, exist_ok=True)
        local_path = local_dir / f'{workflow_name}_local.py'
        local_path.write_text(local_script, encoding='utf-8')
        os.chmod(local_path, 0o755)
        print(f"  💻 Local: {local_path}")

        watch_config = generate_watch_config(workflow_name, local_steps, bridge_info)
        watch_path = local_dir / f'{workflow_name}_watch.txt'
        watch_path.write_text(watch_config, encoding='utf-8')
        print(f"  👁  Watch: {watch_path}")

    print(f"\n✅ 部署完成: {workflow_name}")
    if gha_steps and local_steps:
        print("   1) 推送 .github/workflows/ 到 GitHub")
        print("   2) 配置 GitHub Secrets")
        print("   3) 运行本地 runner: python lwf/runners/{workflow_name}_local.py")


def cmd_list(args):
    """列出目录下的工作流"""
    pattern = str(Path(args.dir or Path.cwd()) / '**/*.yaml')
    from glob import glob
    files = glob(pattern)
    for f in files:
        try:
            data = parse(f)
            gha, local = classify_steps(data['steps'])
            print(f"  {f:<40} GHA:{len(gha)}  Local:{len(local)}")
        except:
            pass


def main():
    parser = argparse.ArgumentParser(
        description='LWF — Lightweight Workflow Framework',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  lwf validate workflows/daily-weather.yaml
  lwf deploy workflows/daily-weather.yaml
  lwf list
        """
    )
    sub = parser.add_subparsers(dest='command')

    # validate
    p = sub.add_parser('validate', help='校验工作流 YAML')
    p.add_argument('workflow', type=Path, help='工作流 YAML 文件')
    p.set_defaults(func=cmd_validate)

    # deploy
    p = sub.add_parser('deploy', help='部署工作流（生成 GHA .yml + 本地 runner）')
    p.add_argument('workflow', type=Path, help='工作流 YAML 文件')
    p.add_argument('--out', '-o', type=Path, default=Path.cwd(),
                   help='输出目录（默认当前目录）')
    p.set_defaults(func=cmd_deploy)

    # list
    p = sub.add_parser('list', help='列出工作流')
    p.add_argument('--dir', '-d', type=Path, help='扫描目录')
    p.set_defaults(func=cmd_list)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == '__main__':
    main()
