# LWF 架构

## 一句话

**GHA 能干的 GHA 干，rclone 做信令，Git 传数据，本地做消费闭环。**

## 架构总览

```bat
┌─────────────────────────────────────────────────────┐
│                 GHA Runner (云端)                    │
│                                                     │
│  detect → collect → process                         │
│     ↓                                               │
│  store/rclone  →  坚果云/自建 NAS                    │
│  (数据 + 信令合二为一)                                │
└─────────────────────────────────────────────────────┘
         │
         │ rclone sync（数据到达即信令）
         ▼
┌─────────────────────────────────────────────────────┐
│                 Rclone Bridge                        │
│  ~/.lwf/bridges/{project}/data/{step_id}.json       │
│  本地 rclone sync 目录，数据同步即触发                │
└─────────────────────────────────────────────────────┘
         │
         │ (1) 检测新文件 → subprocess(runner)
         ▼
┌─────────────────────────────────────────────────────┐
│                  Local Runner (本地)                  │
│                                                     │
│  consume/script (读 data/*.json → 处理)             │
│     ↓                                               │
│  notify/hermes (stdout → Hermes cron → 微信推送)    │
└─────────────────────────────────────────────────────┘
```

## 核心概念

### 双 Runner 分工

| Runner | 运行位置 | 职责 | 能力 |
|--------|---------|------|------|
| **GHA** | GitHub Actions | 定时采集、LLM 处理、rclone 同步 | detect, collect, process, store/rclone |
| **Local** | 本地机器 | 消费同步数据、通知人 | consume, notify/hermes |

### Rclone Bridge（推荐）

**数据与信令合一。** GHA 通过 `store/rclone` 将产出同步到云存储（坚果云/自建 NAS），本地 rclone sync 目录天然检测到新文件 → 触发 Local Runner。

| 桥 | 方向 | 技术 | 用途 |
|----|------|------|------|
| **Rclone Bridge** | GHA → Local | rclone | 传输数据 + 信令（合二为一） |

本地检测机制（任选其一）：
- **Cron 轮询**（推荐）：每 3-5 分钟跑一次，检查 `~/.lwf/bridges/{project}/` 目录有无新文件
- **inotify 监听**：实时检测文件变动，但复杂度高、不可靠
- **Hermes cron**：LWF 未来可集成 Hermes agent 的 cron 能力做统一轮询

### Email Bridge（备选）

邮件作为信令的备选方案。GHA 侧 `notify/email` 发通知邮件，本地侧通过 IMAP 轮询检测新邮件触发。

**经验教训：**
- QQ 邮箱 IMAP 认证不稳定（授权码过期、IP 限流）
- 自建邮箱维护成本高
- 推荐优先用 Rclone Bridge

### Per-step Idle 控制

Local Runner 不再全局跳闸。每步独立决策：

- 默认 (`optional: false`)：`data_file` 不存在 → 打印 "idle — 等待数据"，不执行该步，**但不阻止其他步**
- `optional: true`：`data_file` 不存在 → 打印 "optional — 无数据，跳过"，不执行
- 无 `data_file` 的步（如 `notify/hermes`）：总是执行

## 数据流全链路

```
GHA 定时触发 (cron: "30 7 * * *")
  │
  ├─ detect       ← 检测有无新内容
  ├─ collect      ← 采集原始数据 → data/collect.json
  ├─ process      ← LLM 处理  → data/process.json
  └─ store/rclone ← 同步到坚果云 (数据即信令)
        │
        │ rclone sync 到达本地目录
        ▼
Cron 轮询 (~/.lwf/bridges/{project}/ 有新文件?)
  │
  ├─ 有新文件 → 执行 Local Runner
  │
  ▼
Local Runner
  │
  ├─ consume/script    ← 读 data/*.json → 生成笔记
  └─ notify/hermes     ← Hermes cron → 微信推送
```

## 配置分层

```
workflow.yaml（子项目仓库，公开）
├─ name, trigger.schedule
├─ bridge.rclone.remote      ← rclone remote 名称
├─ bridge.rclone.target      ← 本地同步目标路径
├─ steps[]                   ← 任务步骤定义
│   ├─ GHA 步：collect / process / store/rclone
│   └─ Local 步：consume

~/.lwf/bridges/{project}/    ← 本地同步目录
└─ data/{step_id}.json       ← GHA 同步下来的数据文件
```

## 使用流程

```bash
# 1. 写 workflow.yaml（定义 detect → collect → process → store/rclone）
# 2. 配置 rclone remote（本机）
rclone config

# 3. 部署
lwf deploy sub/ai-daily/workflow.yaml

# 4. 配置本地 cron 轮询
*/5 * * * * ~/.lwf/scripts/bridge-poller.sh

# 5. 推送 GHA workflow 到 GitHub
git push
```
