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

## store — 存储 + 信令（GHA）
| using | config 字段 | 说明 |
|-------|------------|------|
| rclone | remote, type, url, user_secret, pass_secret, source, target | 同步到云存储。**数据即信令** — 本地检测到新文件即触发消费 |

## consume — 消费（Local）
| using | config 字段 | 说明 |
|-------|------------|------|
| script | file, data_file | 消费数据文件 |

支持 `optional: true` 标记 — 无数据时静默跳过。
