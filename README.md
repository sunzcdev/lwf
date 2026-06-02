# LWF — Lightweight Workflow Framework

GHA 能干的 GHA 干，Git 传数据，本地做消费闭环。

## 一句话
框架定义 5 种能力（collect / process / store / notify / consume），子项目 YAML 填空实现。

## 快速开始
```bash
pip install PyYAML jsonschema
python3 -m lwf.cli validate subprojects/_example/workflow.yaml
python3 -m lwf.cli deploy subprojects/_example/workflow.yaml
```

## 新工作流
```bash
cp -r templates/ subprojects/我的项目/
# 编辑 workflow.yaml
lwf deploy subprojects/我的项目/workflow.yaml
git push
```

## 文档
- docs/CAPABILITIES.md — 能力 + config 参考
- docs/CONVENTIONS.md — 数据规范
- docs/GETTING_STARTED.md — 三步上手
