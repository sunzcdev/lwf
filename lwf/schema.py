"""LWF YAML Schema — validates workflow definitions"""

WORKFLOW_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["name", "steps"],
    "properties": {
        "name": {"type": "string", "pattern": "^[a-zA-Z0-9_-]+$"},
        "trigger": {
            "type": "object",
            "properties": {
                "schedule": {"type": "string"},
            }
        },
        "bridge": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["git", "none"]},
                "repo": {"type": "string"},
                "path": {"type": "string"},
            }
        },
        "steps": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["id", "runner", "capability"],
                "properties": {
                    "id": {"type": "string"},
                    "runner": {"type": "string", "enum": ["gha", "local"]},
                    "capability": {
                        "type": "string",
                        "enum": ["collect", "process", "store", "notify", "consume", "detect"]
                    },
                    "using": {"type": "string"},
                    "config": {"type": "object"},
                    "depends": {"type": "array", "items": {"type": "string"}},
                    "optional": {"type": "boolean"},
                    "trigger": {"type": "string", "enum": ["git_push", "schedule", "manual"]},
                }
            }
        }
    }
}
