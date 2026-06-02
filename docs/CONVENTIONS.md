# LWF 数据规范

## 数据桥路径规则
{桥仓库}/bridge/{workflow_name}/data/{YYYY-MM-DD}/{step_id}.json

## 统一数据格式
```json
{
  "workflow": "workflow-name",
  "step_id": "step-id",
  "timestamp": "2026-06-02T07:00:00Z",
  "data": {},
  "meta": {
    "runner": "gha",
    "status": "success"
  }
}
```

## 文件契约
- 每个步骤写 data/{step_id}.json
- 依赖步骤读 data/{depends_id}.json
