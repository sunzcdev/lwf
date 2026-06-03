# LWF v4: 去 Git 桥 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 从 LWF 框架和 ai-daily-learning 子项目中移除所有 Git 桥相关代码，改为纯 artifact + rclone + email 信令架构。

**Architecture:** 三层：GHA（云端全干）→ EmailWatchdog（桥接）→ Local（最后一跳）。数据走 rclone（人看）+ artifact（机器用），信令走 email。

**Tech Stack:** Python, YAML, GitHub Actions, rclone, IMAP

---

### Task 1: schema.py — 删 bridge，加顶层 email

**Files:**
- Modify: `lwf/schema.py`

- [ ] **删除 `bridge.repo` 和 `bridge.path`**

从 `WORKFLOW_SCHEMA.properties.bridge.properties` 中删掉 `repo` 和 `path` 字段。保留 `bridge` 对象但只剩 `email`。

```python
# 改后
"bridge": {
    "type": "object",
    "properties": {
        "email": {
            "type": "object",
            "properties": {
                "triggers": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["subject"],
                        "properties": {
                            "subject": {"type": "string"},
                        }
                    }
                }
            }
        },
    }
},
```

- [ ] **验证**

```bash
cd /home/ubuntu/lwf && python3 -c "
import yaml, json
from lwf.schema import WORKFLOW_SCHEMA
print('schema OK')
# 测试无 bridge 的 workflow
wf = yaml.safe_load('''
name: test
steps:
  - id: x
    runner: gha
    capability: detect
    using: script
    config:
      file: test.sh
''')
from jsonschema import Draft7Validator
errors = list(Draft7Validator(WORKFLOW_SCHEMA).iter_errors(wf))
assert len(errors) == 0, errors
print('validation OK')
"
```

- [ ] **Commit**

```bash
git add lwf/schema.py
git commit -m "refactor: remove bridge.repo/path from schema"
```

---

### Task 2: generators/gha.py — 默认 checkout + rclone 优化

**Files:**
- Modify: `lwf/generators/gha.py`

- [ ] **checkout 步骤改为默认 `actions/checkout@v4`**

找到 `generate()` 函数中的 checkout 步骤，改为：

```python
'      - uses: actions/checkout@v4',
```

去掉 `with:` 中的 `repository` 和 `token` 参数。

- [ ] **标记 `store/git` 能力为废弃**

在 `_render_step()` 的 `store/git` 分支前加注释：

```python
# [deprecated] store/git — Git 桥已取消，优先用 store/rclone
# 代码保留不删，避免已部署的 workflow 报错
```

- [ ] **验证**

运行 `lwf deploy` 看生成的 checkout 步骤是否正确。

- [ ] **Commit**

```bash
git add lwf/generators/gha.py
git commit -m "refactor: default checkout, mark store/git deprecated"
```

---

### Task 3: generators/local.py — 简化，去桥

**Files:**
- Modify: `lwf/generators/local.py`

- [ ] **移除 `BRIDGE_DIR`、`pull()`、`needs_bridge`**

`generate_local()` 中不再生成桥相关代码。`consume/script` 没有 `data_file` 时总是执行脚本（不需要 idle 检测了）。有 `data_file` 时保留检查（兼容旧项目），但检查目录改为当前工作目录。

简化后的 `generate_local()`：

```python
def generate_local(name, local_steps, bridge_info):
    ordered = topo_sort(local_steps)

    lines = [
        '#!/usr/bin/env python3',
        f'"""LWF Local Runner — {name}"""',
        'import json, os, subprocess',
        '',
        'WORK_DIR = os.getcwd()',
        '',
        'def run():',
        f'    print(f"  [lwf] {name}: 开始")',
        '',
    ]

    for s in ordered:
        lines.append(_render_task(s))

    lines.append('')
    lines.append("if __name__ == '__main__':")
    lines.append('    run()')
    for s in ordered:
        lines.append(f'    task_{s["id"]}()')

    return '\n'.join(lines)
```

同时更新 `_render_task()` 中 `consume/script` 的 data_file 检查：去掉 `BRIDGE_DIR`，改为 `os.path.join(WORK_DIR, data_file)`。

- [ ] **验证**

```bash
cd /home/ubuntu/lwf && python3 -c "
import sys; sys.path.insert(0, 'lwf')
from generators.local import generate_local

# 纯 notify/hermes
steps = [{'id': 'n', 'capability': 'notify', 'using': 'hermes', 'config': {'message': 'hi'}}]
code = generate_local('test', steps, {})
assert 'BRIDGE_DIR' not in code
assert 'pull()' not in code
print('✅ no bridge code')

# consume with data_file
steps2 = [{'id': 'c', 'capability': 'consume', 'using': 'script', 'config': {'file': 'x.py', 'data_file': 'd.json'}}]
code2 = generate_local('test2', steps2, {})
assert 'WORK_DIR' in code2
print('✅ consume without bridge')
"
```

- [ ] **Commit**

```bash
git add lwf/generators/local.py
git commit -m "refactor: remove bridge code from local generator"
```

---

### Task 4: cli.py — 去桥部署 + email 从顶层读取

**Files:**
- Modify: `lwf/cli.py`

- [ ] **`cmd_deploy` 中从顶层 `email` 字段读取 trigger**

```python
def cmd_deploy(args):
    data = load(args.workflow)
    validate(data)
    name = data['name']
    gha_steps, local_steps = classify(data['steps'])
    out = Path(args.out or Path.cwd())

    if gha_steps:
        schedule = data.get('trigger', {}).get('schedule')
        yml = gen_gha(name, gha_steps, schedule)  # 不再传 bridge_info
        d = out / '.github' / 'workflows'
        d.mkdir(parents=True, exist_ok=True)
        (d / f'{name}.yml').write_text(yml)
        print(f"  📄 {d / name}.yml")

    if local_steps:
        py = generate_local(name, local_steps)  # 不再传 bridge_info
        d = out / 'lwf' / 'runners'
        d.mkdir(parents=True, exist_ok=True)
        p = d / f'{name}_local.py'
        p.write_text(py)
        p.chmod(0o755)
        print(f"  💻 {p}")

        # ── 从顶层 email 字段读取 trigger ──
        triggers = data.get('email', {}).get('triggers', [])
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
```

- [ ] **更新 `gen_gha` 和 `generate_local` 调用签名**

`gen_gha(name, gha_steps, schedule, bridge)` → `gen_gha(name, gha_steps, schedule)`
`generate_local(name, local_steps, bridge)` → `generate_local(name, local_steps)`

更新 `gha.py` 中 `generate()` 函数签名。

- [ ] **Commit**

```bash
git add lwf/cli.py lwf/generators/gha.py lwf/generators/local.py
git commit -m "refactor: deploy reads email from top level"
```

---

### Task 5: 文档更新

**Files:**
- Modify: `lwf/docs/ARCHITECTURE.md`
- Modify: `lwf/docs/CAPABILITIES.md`
- Modify: `lwf/README.md`

- [ ] **重写 ARCHITECTURE.md**

架构图改为三层：GHA → EmailWatchdog → Local。删所有 Git Bridge、双桥、pull() 相关内容。

核心架构图：

```text
┌─────────────────────────────────────────────┐
│             GHA Runner (云端)                  │
│  detect → collect → process/llm              │
│  store/rclone (云盘)                         │
│  upload-artifact (给本地)                    │
│  notify/email (信令)                         │
└──────────────────┬──────────────────────────┘
                   │ notify/email
                   ▼
┌─────────────────────────────────────────────┐
│           Email Watchdog (桥接)               │
│  IMAP 轮询 → 匹配 subject → subprocess       │
└──────────────────┬──────────────────────────┘
                   │ 触发
                   ▼
┌─────────────────────────────────────────────┐
│           Local Runner (最后一跳)              │
│  consume/script (下载 artifact + 消费)       │
│  notify/hermes (微信通知)                    │
└─────────────────────────────────────────────┘
```

- [ ] **更新 CAPABILITIES.md**

`store/git` → 标记为废弃。`store/rclone` → 提升为首选。删 `archive` 等不存在的能力。

- [ ] **更新 README**

- [ ] **Commit**

```bash
git add docs/ARCHITECTURE.md docs/CAPABILITIES.md README.md
git commit -m "docs: update for v4 no-git-bridge architecture"
```

---

### Task 6: 推送 LWF 框架改动

- [ ] **推送**

```bash
git push
```

---

### Task 7: ai-daily-learning workflow.yaml 更新

**Files:**
- Modify: `/tmp/ai-daily-learning/workflow.yaml`

- [ ] **写新 workflow.yaml**

```yaml
name: ai-daily-learning
trigger:
  schedule: "30 23 * * *"

email:
  triggers:
    - subject: "✅ ai-daily-learning"

steps:
  - id: get-plan
    runner: gha
    capability: detect
    using: script
    config:
      file: scripts/detect-topic.sh

  - id: fetch
    runner: gha
    depends: [get-plan]
    capability: collect
    using: script
    config:
      file: scripts/fetch-chapter.py
      args: ${{ steps.get-plan.outputs.topic }}

  - id: generate
    runner: gha
    depends: [fetch]
    capability: process
    using: llm
    config:
      model: "gpt-4o"
      api_url: "https://models.github.ai/inference/v1/chat/completions"
      system_prompt: "${{ vars.SYSTEM_PROMPT }}"
      prompt: |
        把下面内容改写成预习笔记：
        1. 用自己的话复述核心概念
        2. 配一两个日常例子
        3. 写一段「一句话总结」

        原文如下：

  - id: update-state
    runner: gha
    depends: [generate]
    capability: process
    using: script
    config:
      file: scripts/update-state.sh
      args: ${{ steps.get-plan.outputs.day }}

  - id: sync-obsidian
    runner: gha
    depends: [generate]
    capability: store
    using: rclone
    config:
      remote: "jianguoyun"
      type: "webdav"
      url: "https://dav.jianguoyun.com/dav/"
      vendor: "other"
      user_secret: "RCLONE_USER"
      pass_secret: "RCLONE_PASS"
      source: "data/"
      target: "notebook/学/AI/AI每日学习/"

  - id: notify-email
    runner: gha
    depends: [generate]
    capability: notify
    using: email
    config:
      to: "zhenchao@qq.com"
      subject: "✅ ai-daily-learning"

  - id: consume
    runner: local
    capability: consume
    using: script
    config:
      file: scripts/consume-local.sh

  - id: notify-wechat
    runner: local
    capability: notify
    using: hermes
    config:
      message: "✅ 今日笔记已同步到 Obsidian"
```

---

### Task 8: ai-daily-learning GHA workflow + 本地脚本

**Files:**
- Create: `/tmp/ai-daily-learning/scripts/consume-local.sh`
- Modify: `/tmp/ai-daily-learning/.github/workflows/ai-daily-learning.yml`

- [ ] **创建 consume-local.sh**

```bash
#!/bin/bash
# consume-local.sh — 下载 artifact + 消费

REPO="sunzcdev/ai-daily-learning"
WORKFLOW="ai-daily-learning"
LWF_DIR="$HOME/.lwf/artifacts/ai-daily-learning"

RUN_ID=$(gh run list --repo "$REPO" \
  --workflow "$WORKFLOW" --status success --limit 1 \
  --json databaseId --jq '.[0].databaseId')

if [ -z "$RUN_ID" ]; then
  echo "  ! 没有成功的 workflow run"
  exit 0
fi

rm -rf "$LWF_DIR"
mkdir -p "$LWF_DIR"
gh run download "$RUN_ID" --repo "$REPO" --dir "$LWF_DIR"

echo "  ✓ artifact $RUN_ID 已下载"

# 消费
python3 scripts/write-obsidian.py
```

- [ ] **写 GHA workflow**

参考 `docs/SUBPROJECT_GUIDE.md` 中的模板，包含：
- 默认 `actions/checkout@v4`（无 BRIDGE_REPO）
- `gpt-4o` + `system_prompt` 走 env 变量
- `store/rclone` 步骤
- `notify/email` 步骤
- `upload-artifact` + `probe-output`

- [ ] **run `lwf deploy` 生成 local runner + watchdog config**

```bash
cd /home/ubuntu/lwf && python -m lwf.cli deploy /tmp/ai-daily-learning/workflow.yaml --out /tmp/ai-daily-learning
```

- [ ] **提交**

```bash
cd /tmp/ai-daily-learning
git add -A
git commit -m "feat: migrate to v4 no-git-bridge architecture"
git push
```
