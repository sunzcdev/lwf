# LWF 框架·架构设计 v0.1

## 一、核心理念

> GHA 能干的 GHA 干 → 数据桥传递 → 干不了的本机干 → 可选闭环

框架的价值不在于代码，在于**一套约定**。任何新项目只要遵守这套约定，就自动获得：
- 定时触发能力（GHA cron）
- 数据持久化 + 可追溯（Git 桥）
- 多端通知（邮件 / 微信）
- 本地自动化（Obsidian / 脚本）

---

## 二、核心抽象（共 4 层）

```
┌─────────────────────────────────────────────┐
│  Workflow  ─  工作流 YAML 定义               │
│  ├─ trigger: 怎么触发                        │
│  ├─ bridge:  数据怎么传递                    │
│  └─ steps[]: 每一步做什么                     │
├─────────────────────────────────────────────┤
│  Step  ─  一个最小执行单元                    │
│  ├─ 输入: 依赖的上一步文件 data/{id}.json    │
│  ├─ 执行: 由 runner 决定环境                 │
│  └─ 输出: 写入 data/{id}.json                │
├─────────────────────────────────────────────┤
│  Runner  ─  执行环境                         │
│  ├─ gha:   GitHub Actions（云端）            │
│  └─ local: 本机执行（Hermes）               │
├─────────────────────────────────────────────┤
│  Bridge  ─  数据传递层                       │
│  ├─ git:   GitHub 仓库（默认）              │
│  ├─ none:  无桥（单端执行）                 │
│  └─ 未来: 可扩展其他桥类型                   │
└─────────────────────────────────────────────┘
```

### 2.1 Workflow

一条工作流 = 一个 YAML 文件。框架核心职责：解析 YAML → 生成 GHA .yml + 本地 runner。

### 2.2 Step

每个 step 遵循**文件契约**：
- 读输入：`data/{depends_id}.json`（自动从依赖步骤获取）
- 写输出：`data/{自己的id}.json`（自动写入）

步骤之间不直接传变量，通过文件系统隐式通信。这是最轻量的解耦方式。

### 2.3 Runner

Runner 是**声明式映射**——YAML 里写 `runner: gha` 就生成 GHA 代码，写 `runner: local` 就生成本地代码。映射规则固化在 generator 里，新增 runner 只需加一个新 generator。

### 2.4 Bridge

桥是**可配置的数据传输层**。默认 git：
- GHA 侧：`git commit + push` 到桥仓库的约定路径
- 本地侧：`git pull` 从桥仓库拉取最新数据

路径规则：`bridge/{workflow_name}/data/{date}/{step_id}.json`

---

## 三、数据规范（核心约定）

这是框架最重要的部分——**统一数据格式**，所有工作流共用。

### 3.1 目录结构

```
桥仓库 /
  bridge/
    {workflow_name}/          # 每个工作流一个子目录
      data/
        {YYYY-MM-DD}/         # 按日期分
          {step_id}.json      # 各步骤输出
          manifest.json       # （可选）该日期数据清单
```

### 3.2 数据格式

```json
{
  "workflow": "daily-weather",
  "step_id": "weather",
  "timestamp": "2026-06-02T07:00:00Z",
  "data": { /* 步骤输出的实际内容 */ },
  "meta": {
    "runner": "gha",
    "duration_ms": 1234,
    "status": "success"
  }
}
```

所有步骤统一这个 envelope 结构。消费方（本地 runner、通知、Obsidian 模板）只需要解析 `data` 字段，上层结构一致。

### 3.3 消费方适配

| 消费端 | 读什么 | 怎么做 |
|--------|--------|--------|
| Obsidian | `data.content` | 日记 skill 填模板 |
| 微信 | `data.summary` | no_agent 脚本输出 |
| 邮件 | 整条 | 直接发 HTML |
| 知识库 | 整条 | 按日期归档 |

---

## 四、配置分层

```
Layer 1: 工作流 YAML（必须）
  ├── name / trigger / bridge / vars
  └── steps[].{id, runner, action, depends}

Layer 2: GitHub Secrets（运行时）
  ├── LLM_KEY / EMAIL_* / OWM_KEY
  ├── BRIDGE_REPO / BRIDGE_TOKEN
  └── 各步骤自定义 env

Layer 3: 本地配置（~/.lwf/config.yaml）
  ├── bridge_repos: 本地 clone 路径
  ├── poll_interval: 轮询间隔
  └── local_actions: 自定义 action 实现
```

Layer 1 + 2 是必配，Layer 3 是本地优化。

---

## 五、扩展点（适配空间）

### 5.1 新增 action 类型

在 `generators/gha.py` 加一个 `elif t == 'newtype'` 分支 → 定义 GHA 侧生成什么脚本。
在 `generators/local.py` 加一个 `elif t == 'newtype'` 分支 → 定义本地侧行为。

schema.py 的 `action.type` enum 里加一项。

**不需要的 action 类型不实现即可，不会报错。**

### 5.2 新增 runner

新增一个 `generators/newrunner.py`，实现 `generate(steps) → 脚本`。
在 CLI 里加一个 `--runner newrunner` 选项。
Schema 里 `runner` enum 加一项。

### 5.3 新增桥类型

桥是数据层抽象，目前只有 `git` 和 `none`。
未来可加 `s3`、`webhook`、`local_fs`——但只在有人需要时再加。

### 5.4 插件式 action

远期可考虑：action 支持 `type: custom` + `script: path/to/handler.py`，由用户自定义实现，框架只负责编排和传参。

---

## 六、设计决策记录

| 决策 | 选项 | 选定 | 理由 |
|------|------|------|------|
| 步骤间通信 | 变量传递 / 文件契约 | 文件契约 | 零耦合，GHA 和本地都适用 |
| 桥路径 | 可配置 | `bridge/{name}/data/{date}/` | 统一，按工作流隔离 |
| 模板解析 | Jinja2 / shell envsubst | 不解析 | 保持零依赖，YAML 只是配置声明 |
| LLM 提供商 | 硬编码 / 配置 | 写在 YAML `action.model` | 每个步骤可独立指定 |
| 本地触发 | cron / webhook / 轮询 | 配置可选 | 默认轮询，需要再加 |

---

## 七、当前进度

```
✅ Schema 定义（JSON Schema + 校验规则）
✅ Parser（加载 + 校验 + DAG 排序）
✅ GHA Generator（6 种 action: http/llm/git/email/script/trigger）
✅ Local Generator（3 种 action: obsidian/wechat/gha-trigger）
✅ CLI（validate / deploy / list）
✅ 示例工作流（daily-weather）

❌ 桥仓库 & 数据规范   ← 你已确认方向
❌ 本地轮询 cron 配置   ← 等你定频率
❌ 闭环触发              ← 你说"可选"
❌ 第一个真实闭环跑通    ← 以上确认后开跑
```
