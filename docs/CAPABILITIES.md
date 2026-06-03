# LWF 能力手册

## detect — 检测（GHA）
| using | config 字段 | 说明 |
|-------|------------|------|
| script | file | bash 检测脚本 |

## collect — 采集（GHA）
| using | config 字段 | 说明 |
|-------|------------|------|
| http | url, method | HTTP 请求 → data/{id}.json |
| script | file, args | 脚本采集 |

## process — 处理（GHA）
| using | config 字段 | 说明 |
|-------|------------|------|
| llm | model, api_url, prompt | LLM API → data/{id}.json |
| script | file, args | 脚本处理 |

## store — 存储（GHA）
| using | config 字段 | 说明 |
|-------|------------|------|
| git | commit_message | commit + push 到桥仓库 |
| rclone | remote, type, url, user_secret, pass_secret, source, target | 同步到云存储 |

## notify — 通知（GHA）
| using | config 字段 | 说明 |
|-------|------------|------|
| email | to, subject | 发通知邮件（也作为 Local 触发的信令） |

## consume — 消费（Local）
| using | config 字段 | 说明 |
|-------|------------|------|
| script | file, data_file | 消费数据文件 |

支持 `optional: true` 标记 — 无数据时静默跳过。

## 看门狗（Local，框架基础设施）
Email Watchdog 轮询 IMAP 收件箱，匹配 GHA `notify/email` 的邮件主题 → 触发 Local Runner。
配置见 docs/ARCHITECTURE.md。
