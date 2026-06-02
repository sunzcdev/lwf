# ai-briefing — AI 资讯简报 LWF 子项目

## 概述

AI 资讯自动采集、LLM 精选、邮件推送系统。每日/周/月自动运行。
使用 LWF 框架编排，原有采集逻辑保持不变。

## 数据结构

```
数据桥: bridge/ai-briefing/data/{YYYY-MM-DD}/
  ├── collect.json   — 原始采集结果
  ├── digest.json    — LLM 精选结果
  └── send.json      — 发送确认
```

## Secrets 配置

| Secret | 说明 |
|--------|------|
| GITHUB_TOKEN | GitHub API 访问（采集用） |
| LLM_KEY | 硅基流动 API Key（精选用） |
| QQ_SMTP_PASS | QQ 邮箱授权码（发信用） |
| EMAIL_TO | 收件人地址 |
| BRIDGE_REPO | 数据桥仓库 (sunzcdev/data-bridge) |
| BRIDGE_TOKEN | 桥仓库写入 token |
