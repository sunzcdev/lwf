# LWF v4：去 Git 桥，纯 Artifact + Email 信令架构

## 背景

LWF 原架构依赖 Git 桥仓库在 GHA 和 Local Runner 之间传输数据。实际使用中发现：
- Git 桥引入不必要的 commit 污染和仓库膨胀
- GHA 的 `store/rclone` 已能直写云盘（人看），`upload-artifact` 已能供本地使用（机器用）
- Git 在数据通路中没有不可替代的位置

## 新架构

```
┌─────────────────────────────────────────────────┐
│                 GHA Runner (云端)                  │
│                                                   │
│  detect/script → collect/* → process/llm          │
│      ↓ (写入 data/{step_id}.json)                  │
│  store/rclone (同步云盘，人看)                     │
│  upload-artifact (保留 data/，给本地用)             │
│  notify/email (信令 → IMAP)                       │
└──────────────────┬──────────────────────────────┘
                   │ notify/email
                   ▼
┌─────────────────────────────────────────────────┐
│              Email Watchdog (桥接)                │
│                                                   │
│  IMAP 轮询 → 匹配 subject → subprocess(runner)    │
└──────────────────┬──────────────────────────────┘
                   │ 触发
                   ▼
┌─────────────────────────────────────────────────┐
│               Local Runner (本地)                  │
│                                                   │
│  consume/script: 下载 artifact → 处理数据         │
│  notify/hermes: 微信通知                          │
└─────────────────────────────────────────────────┘
```

### 三大职责

| 块 | 职责 | 能力 |
|----|------|------|
| **GHA** | 所有能云端操作的步骤 | detect, collect, process, store/rclone, notify/email |
| **桥接** | 信令传递 | EmailWatchdog (IMAP 轮询 + 主题匹配 + subprocess) |
| **Local** | 云端做不了的事 | consume/script (下载 artifact + 消费), notify/hermes |

### 数据流

```
GHA:
  1. detect: 读 GitHub Variable → 决定今天学什么
  2. collect: 采集原始数据 → data/fetch.json
  3. process/llm: LLM 生成笔记 → data/generate.json
  4. store/rclone: 同步 data/ → 坚果云 (人看)
  5. upload-artifact: data/ → artifact (机器用)
  6. notify/email: 发邮件 "✅ xxx" (信令)

桥接:
  7. EmailWatchdog 轮询 IMAP → 匹配 subject → 执行 local runner

Local:
  8. consume/script: 下载 artifact → 消费数据
  9. notify/hermes: 微信通知
```

## 框架改动清单

### 1. schema.py

- 删 `bridge.repo`, `bridge.path`
- `bridge.email` → 顶层 `email` 字段

### 2. generators/gha.py

- `checkout` 步骤：改回默认 `actions/checkout@v4`（不加 BRIDGE_REPO/BRIDGE_TOKEN）
- `store/git` 能力标记废弃（不删代码，加注释）

### 3. generators/local.py

- 删 `BRIDGE_DIR`、`pull()` 相关代码
- `consume/script` 改为「下载 artifact + 消费」模式
  - 通过 `gh run download` 获取最新 artifact
  - 需配置仓库名（从 workflow 的 `lwf/runners/d/{name}.yaml` 获取）

### 4. CLI

- 删 `bridge` 相关参数
- `deploy` 不再读写 `bridge.repo`/`bridge.path`
- `watchdog.d/{name}.yaml` 从 `email.triggers` 生成

### 5. Email Watchdog

- 不动。仍然通过 `~/.lwf/watchdog.yaml` (IMAP) + `~/.lwf/watchdog.d/{name}.yaml` (triggers) 工作
- triggers 来源从 `bridge.email.triggers` 改为 `email.triggers`

### 6. 架构文档 (ARCHITECTURE.md)

- 删所有 Git Bridge 相关内容
- 删"双桥"概念
- 新图反映纯 artifact + rclone 数据通路

### 7. 能力手册 (CAPABILITIES.md)

- `store/git` → 标记废弃
- `store/rclone` → 提升为默认存储方式
- 明确 artifact 作为本地数据通道

## 子项目 (ai-daily-learning) 改动

### workflow.yaml

```yaml
name: ai-daily-learning
trigger:
  schedule: "30 23 * * *"

email:
  triggers:
    - subject: "✅ ai-daily-learning"

steps:
  - id: get-plan       runner: gha  capability: detect/script
  - id: fetch          runner: gha  capability: collect/script
  - id: generate       runner: gha  capability: process/llm
  - id: update-state   runner: gha  capability: process/script
  - id: sync-obsidian  runner: gha  capability: store/rclone
  - id: notify-email   runner: gha  capability: notify/email

  - id: consume        runner: local  capability: consume/script
  - id: notify-wechat  runner: local  capability: notify/hermes
```

### consume/script 脚本

本地消费脚本需要从 artifact 获取数据。通过 `gh run download` 下载最新 artifact：

```bash
RUN_ID=$(gh run list --repo sunzcdev/ai-daily-learning \
  --workflow ai-daily-learning --status success --limit 1 \
  --json databaseId --jq '.[0].databaseId')
gh run download "$RUN_ID" --repo sunzcdev/ai-daily-learning --dir ~/.lwf/artifacts/ai-daily-learning/
# 然后读取 data/generate.json 等
```

### GHA workflow

- `checkout` 用默认（不加 BRIDGE_REPO/BRIDGE_TOKEN）
- 添加 rclone 同步步骤（`RCLONE_CONFIG_*` 环境变量注入）
- `upload-artifact` 保留（已有 probe-output 条件上传）

## 不改的部分

- `store/rclone` 能力 —— 不动
- `notify/email` 能力 —— 不动
- `notify/hermes` 能力 —— 不动
- `EmailWatchdog` —— 不动
- Per-step `optional` 控制 —— 不动
- `detect/script`、`collect/*`、`process/*` —— 不动
- probe-output + conditional artifact upload —— 不动
