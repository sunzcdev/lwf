"""LWF CLI — validate / deploy / list"""

import argparse, sys
from pathlib import Path
from .parser import load, validate, classify
from .generators.gha import generate as gen_gha
from .generators.local import generate_local


def cmd_validate(args):
    data = load(args.workflow)
    validate(data)
    gha, local = classify(data['steps'])
    print(f"✅ {args.workflow.name} 校验通过")
    print(f"   GHA: {len(gha)}步 | Local: {len(local)}步")


def cmd_deploy(args):
    data = load(args.workflow)
    validate(data)
    name = data['name']
    gha_steps, local_steps = classify(data['steps'])
    out = Path(args.out or Path.cwd())

    if gha_steps:
        schedule = data.get('trigger', {}).get('schedule')
        yml = gen_gha(name, gha_steps, schedule)
        d = out / '.github' / 'workflows'
        d.mkdir(parents=True, exist_ok=True)
        (d / f'{name}.yml').write_text(yml)
        print(f"  📄 {d / name}.yml")

    if local_steps:
        bridge = data.get('bridge', {})
        py = generate_local(name, local_steps, bridge)
        d = out / 'lwf' / 'runners'
        d.mkdir(parents=True, exist_ok=True)
        p = d / f'{name}_local.py'
        p.write_text(py)
        p.chmod(0o755)
        print(f"  💻 {p}")

    print(f"\n✅ 部署完成: {name}")


def main():
    p = argparse.ArgumentParser(description='LWF — Lightweight Workflow Framework')
    sub = p.add_subparsers(dest='cmd')

    v = sub.add_parser('validate', help='校验工作流')
    v.add_argument('workflow', type=Path)
    v.set_defaults(func=cmd_validate)

    d = sub.add_parser('deploy', help='部署工作流')
    d.add_argument('workflow', type=Path)
    d.add_argument('--out', '-o', type=Path, default=Path.cwd())
    d.set_defaults(func=cmd_deploy)

    args = p.parse_args()
    if not args.cmd:
        p.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == '__main__':
    main()
