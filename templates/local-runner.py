#!/usr/bin/env python3
"""本地消费 runner — 子项目改对应的实现"""
import json, os, subprocess
from pathlib import Path

BRIDGE_DIR = os.path.expanduser("~/.lwf/bridges/")

def pull():
    subprocess.run(["git", "-C", os.path.dirname(BRIDGE_DIR), "pull"])

def do_obsidian(config):
    vault = os.path.expanduser(config.get("vault_path", "~/notebook"))
    folder = config.get("folder", "")
    target = Path(vault) / folder
    target.mkdir(parents=True, exist_ok=True)
    print(f"[lwf] Obsidian 目标: {target}")

def do_archive(config):
    print(f"[lwf] 归档: {config}")

if __name__ == "__main__":
    pull()
    print("[lwf] 本地 runner 就绪，请在 __main__ 中实现消费逻辑")
