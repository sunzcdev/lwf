"""工作流 YAML JSON Schema 定义"""

WORKFLOW_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["name", "steps"],
    "properties": {
        "name": {
            "type": "string",
            "description": "工作流名称，用作 GHA workflow 文件名",
            "pattern": "^[a-zA-Z0-9_-]+$"
        },
        "version": {
            "type": "integer",
            "default": 1,
            "description": "Schema 版本"
        },
        "trigger": {
            "type": "object",
            "properties": {
                "schedule": {
                    "type": "string",
                    "description": "cron 表达式（UTC），如 '0 23 * * *' = 北京 7:00"
                },
                "webhook": {
                    "type": "boolean",
                    "default": False,
                    "description": "是否支持 webhook 触发"
                }
            }
        },
        "bridge": {
            "type": "object",
            "description": "数据桥配置，定义数据如何在 GHA 和本地之间流转",
            "required": ["type"],
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["git", "none"],
                    "description": "桥类型：git 走仓库，none 无数据桥"
                },
                "repo": {
                    "type": "string",
                    "description": "数据桥仓库（如 sunzcdev/data-bridge）"
                },
                "path": {
                    "type": "string",
                    "description": "该工作流在桥仓库中的子路径"
                }
            }
        },
        "vars": {
            "type": "object",
            "description": "全局变量，可在各步骤中引用",
            "additionalProperties": {"type": "string"}
        },
        "steps": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["id", "runner", "action"],
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "步骤唯一 ID，供 depends 引用"
                    },
                    "runner": {
                        "type": "string",
                        "enum": ["gha", "local"],
                        "description": "执行环境：gha（GitHub Actions）或 local（本机）"
                    },
                    "depends": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "依赖的上一步 ID 列表"
                    },
                    "optional": {
                        "type": "boolean",
                        "default": False,
                        "description": "失败是否不影响后续步骤"
                    },
                    "trigger": {
                        "type": "string",
                        "enum": ["git_push", "schedule", "manual"],
                        "description": "local runner 的触发方式"
                    },
                    "action": {
                        "type": "object",
                        "required": ["type"],
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": [
                                    "http", "llm", "script", "write",
                                    "git", "email", "obsidian", "wechat",
                                    "gha-trigger"
                                ]
                            },
                            "url": {"type": "string"},
                            "method": {"type": "string", "default": "GET"},
                            "headers": {"type": "object"},
                            "model": {"type": "string"},
                            "prompt": {"type": "string"},
                            "file": {"type": "string"},
                            "path": {"type": "string"},
                            "content": {"type": "string"},
                            "template": {"type": "string"},
                            "data": {"type": "string"},
                            "to": {"type": "string"},
                            "subject": {"type": "string"},
                            "body": {"type": "string"},
                            "commit": {"type": "string"},
                            "workflow": {"type": "string"},
                            "inputs": {"type": "object"},
                            "env": {
                                "type": "object",
                                "description": "环境变量，值可引用 {{ secrets.XXX }}"
                            }
                        }
                    },
                    "outputs": {
                        "type": "object",
                        "description": "输出定义，供后续步骤引用",
                        "additionalProperties": {"type": "string"}
                    }
                }
            }
        }
    }
}
