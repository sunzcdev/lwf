# LWF 快速开始

## 安装
```bash
pip install PyYAML jsonschema
git clone https://github.com/YOUR_ORG/lwf.git
cd lwf
```

## 创建新工作流
```bash
cp -r templates/ subprojects/我的项目/
# 编辑 subprojects/我的项目/workflow.yaml
python3 -m lwf.cli validate subprojects/我的项目/workflow.yaml
python3 -m lwf.cli deploy subprojects/我的项目/workflow.yaml
```

## 推送到 GitHub
生成的 .github/workflows/*.yml 和 lwf/runners/* 一起提交推送。
在 GitHub 仓库配置 Secrets。
