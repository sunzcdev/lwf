# LWF — Lightweight Workflow Framework

## 理念

```
GHA 能干的 GHA 干 → Git 做数据桥 → 干不了的本机干 → 闭环再触发 GHA
```

配置优先，脚本其次，最少依赖。

## 安装

```bash
pip install -e .
# 或
pip install PyYAML jsonschema
export PATH="$PATH:$(pwd)"
```

## 用法

```bash
# 校验工作流定义
lwf validate examples/daily-weather.yaml

# 部署：生成 GHA .yml + 本地 runner
lwf deploy examples/daily-weather.yaml

# 列出工作流
lwf list
```

## 架构

- **GHA Runner** — 定时触发、HTTP 采集、LLM 处理、Git Push
- **数据桥** — GitHub 仓库，GHA 写、本地读
- **Local Runner** — 检测新数据、写 Obsidian、微信推送
- **闭环** — 本地处理后可通过 `gh workflow run` 触发新一轮

## 支持 Action 类型

| 类型 | Runner | 说明 |
|------|--------|------|
| `http` | gha | HTTP 请求采集 |
| `llm` | gha | LLM API 调用 |
| `script` | gha | 运行 Python 脚本 |
| `write` | gha | 写入文件 |
| `git` | gha | 提交推送 |
| `email` | gha | SMTP 邮件通知 |
| `gha-trigger` | both | 触发其他工作流 |
| `obsidian` | local | 写入 Obsidian 日记 |
| `wechat` | local | 微信推送 |
