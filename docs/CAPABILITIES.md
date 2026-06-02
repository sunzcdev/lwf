# LWF 能力手册

## collect — 采集
| using | config 字段 | 说明 |
|-------|------------|------|
| http | url, method, headers | HTTP 请求 |
| rss | url | RSS 订阅 |
| github | topic, stars | GitHub 搜索 |
| file | path | 本地文件 |

## process — 处理
| using | config 字段 | 说明 |
|-------|------------|------|
| llm | api_url, api_key, model, prompt | LLM API |
| script | file | Python 脚本 |
| filter | condition | 数据过滤 |

## store — 存储
| using | config 字段 | 说明 |
|-------|------------|------|
| git | commit_message | 提交到桥仓库 |
| local | path | 本地存储 |
| none | — | 不存储 |

## notify — 通知
| using | config 字段 | 说明 |
|-------|------------|------|
| email | smtp_*, from, to, subject | SMTP 邮件 |
| wechat | webhook, secret | 企业微信 |

## consume — 本地消费
| using | config 字段 | 说明 |
|-------|------------|------|
| obsidian | vault_path, folder, template | 写入 Obsidian |
| archive | target_dir | 归档 |
| webhook | url | HTTP 回调 |
