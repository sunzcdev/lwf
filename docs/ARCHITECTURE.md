# LWF 架构

## 一句话

**GHA 能干的 GHA 干，邮件做信令，Git 传数据，本地做消费闭环。**

## 架构总览

```
┌──────────────────────────────────────────────────────────────────┐
│                       GHA Runner (云端)                          │
│                                                                  │
│  detect/script ──→ collect/http ──→ process/llm ──→ store/git   │
│                                                          ↓       │
│                                                     notify/email │
└──────────────────────────────────────────────────────────────────┘
         │                                       │
         │ (1) Git push 数据                      │ (2) 发送通知邮件
         ▼                                       ▼
┌─────────────────────────────────┐  ┌─────────────────────────────┐
│         Git Bridge              │  │      Email Bridge           │
│  ~/.lwf/bridges/{repo}/...      │  │  IMAP 收件箱 (QQ/163/Gmail) │
│  data/{step_id}.json            │  │  主题匹配 trigger           │
└─────────────────────────────────┘  └──────────┬──────────────────┘
         ▲                                      │
         │ (3) pull 获取数据                     │ (4) 检测到 → 触发
         │                                      ▼
┌──────────────────────────────────────────────────────────────────┐
│                    Email Watchdog (lwf watchdog)                 │
│                                                                  │
│  ┌────────────────────────────────────────────┐                  │
│  │  IMAP 轮询 (每 60 秒)                      │                  │
│  │  → 搜索 UNSEEN SUBJECT "✅ ai-*-learning"  │                  │
│  │  → 匹配 → subprocess(runner)               │                  │
│  │  → 标记已读                                │                  │
│  └────────────────────────────────────────────┘                  │
└──────────────────────────────────────────────────────────────────┘
         │
         │ (5) 执行
         ▼
┌──────────────────────────────────────────────────────────────────┐
│                      Local Runner (本地)                         │
│                                                                  │
│  pull() → 同步 Git Bridge                                       │
│     ↓                                                           │
│  consume/script (检查 data_file → 有数据就处理)                  │
│     ↓                                                           │
│  notify/hermes (stdout → Hermes cron → 微信推送)                │
└──────────────────────────────────────────────────────────────────┘
```

## 核心概念

### 双 Runner 分工

| Runner | 运行位置 | 职责 | 能力 |
|--------|---------|------|------|
| **GHA** | GitHub Actions | 定时采集、LLM 处理、数据持久化、发信令 | detect, collect, process, store, notify/email |
| **Local** | 本地机器 | 消费数据、做需要本地资源的操作、通知人 | consume, notify/hermes |

### 双桥机制

数据流和信令流分离：

| 桥 | 方向 | 技术 | 用途 |
|----|------|------|------|
| **Git Bridge** | GHA → Local | Git pull/push | 传输数据 (JSON) |
| **Email Bridge** | GHA → Local | IMAP + SMTP | 传输信令 (通知/触发) |

### Email Watchdog

LWF 框架基础设施，独立守护进程：

```
~/.lwf/
├── watchdog.yaml         ← 全局 IMAP 凭证（本机配置，不进仓库）
└── watchdog.d/
    ├── ai-daily-learning.yaml   ← 由 lwf deploy 自动生成
    └── xxx.yaml                  ← 每部署一个子项目就多一个
```

每个 `watchdog.d/{name}.yaml` 定义：

```yaml
runner: ~/.lwf/runners/ai-daily-learning_local.py   # 触发的脚本
triggers:
  - subject: "✅ ai-daily-learning"    # 匹配 GHA 发来的邮件主题
```

### Per-step Idle 控制

Local Runner 不再全局跳闸。每步独立决策：

- 默认 (`optional: false`)：`data_file` 不存在 → 打印 "idle — 等待数据"，不执行该步，**但不阻止其他步**
- `optional: true`：`data_file` 不存在 → 打印 "optional — 无数据，跳过"，不执行
- 无 `data_file` 的步（如 `notify/hermes`）：总是执行

## 数据流全链路

```
GHA 定时触发 (cron: "30 7 * * *")
  │
  ├─ detect/script     ← 检测有无新内容
  ├─ collect/http      ← 采集原始数据 → data/collect.json
  ├─ process/llm       ← LLM 处理  → data/process.json
  ├─ store/git         ← commit + push 到桥仓库
  ├─ notify/email      ← 发通知邮件 "✅ ai-daily-learning"
  │
  ▼  (邮件到达 IMAP 收件箱)
  │
Email Watchdog 轮询到 UNSEEN 邮件
  │
  ├─ 匹配 subject → 执行 lwf/runners/ai-daily-learning_local.py
  │
  ▼
Local Runner
  │
  ├─ pull()            ← 同步桥仓库
  ├─ consume/script    ← 读 data/*.json → 生成笔记
  └─ notify/hermes     ← print 消息 → Hermes cron → 微信推送
```

## 配置分层

```
workflow.yaml（子项目仓库，公开）
├─ name, trigger.schedule
├─ bridge.repo, bridge.path
├─ bridge.email.triggers      ← 邮件触发规则（非敏感）
├─ steps[]                    ← 任务步骤定义
│   ├─ GHA 步：collect / process / store / notify
│   └─ Local 步：consume

~/.lwf/watchdog.yaml（本机，不进仓库）
└─ imap.host, imap.user, imap.pass    ← IMAP 凭证

~/.lwf/watchdog.d/{name}.yaml（自动生成）
└─ runner, triggers[]                  ← 由 lwf deploy 写入
```

## 使用流程

```bash
# 1. 写 workflow.yaml
# 2. 配置 bridge.email.triggers（子项目）
# 3. 部署
lwf deploy sub/ai-daily/workflow.yaml

# 4. 配置本机 IMAP 凭证
vim ~/.lwf/watchdog.yaml

# 5. 启动守护进程
lwf watchdog start

# 6. 推送 GHA workflow 到 GitHub
git push
```
