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
        bridge = data.get('bridge', {})
        yml = gen_gha(name, gha_steps, schedule, bridge)
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

        # ── 写 email trigger 配置 ──
        email_cfg = bridge.get('email', {})
        triggers = email_cfg.get('triggers', [])
        if triggers:
            wd_dir = Path.home() / '.lwf' / 'watchdog.d'
            wd_dir.mkdir(parents=True, exist_ok=True)
            trigger_cfg = {
                'runner': str(p),
                'triggers': triggers,
            }
            wd_path = wd_dir / f'{name}.yaml'
            import yaml
            wd_path.write_text(yaml.dump(trigger_cfg, allow_unicode=True, default_flow_style=False))
            print(f"  📧 {wd_path} ({len(triggers)} 个 trigger)")

    print(f"\n✅ 部署完成: {name}")


def cmd_watchdog(args):
    from .watchdog.email import EmailWatchdog

    wd = EmailWatchdog(config_path=args.config)
    if args.action == "once":
        wd.poll_once()
    elif args.action == "start":
        wd.run_forever(interval=args.interval)

    print("✅ 已完成")


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

    w = sub.add_parser('watchdog', help='启动本地邮箱看门狗')
    w.add_argument('action', choices=['once', 'start'], help='once=单次轮询, start=持续运行')
    w.add_argument('--config', default='~/.lwf/watchdog.yaml', help='看门狗配置文件路径')
    w.add_argument('--interval', '-i', type=int, default=60, help='轮询间隔（秒）')
    w.set_defaults(func=cmd_watchdog)

    args = p.parse_args()
    if not args.cmd:
        p.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == '__main__':
    main()
