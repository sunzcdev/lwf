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
lwf validate subprojects/我的项目/workflow.yaml
lwf deploy subprojects/我的项目/workflow.yaml
```

## 配置 Rclone 桥（可选，Local Runner 需要）
```bash
# 1. 配置 rclone remote（用于 GHA 同步 + 本地检测）
rclone config

# 2. 添加 cron 轮询
crontab -e
# 添加：*/5 * * * * ~/.lwf/scripts/bridge-poller.sh
```

## 推送到 GitHub
```bash
git add -A && git commit -m "add workflow"
git push
```

在 GitHub 仓库配置 Secrets（LLM_KEY、EMAIL_PASS 等）。
