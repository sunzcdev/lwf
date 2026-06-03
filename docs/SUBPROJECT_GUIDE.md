# LWF 子项目搭建指南 (v4)

## 一句话

**GHA 干所有云端能做的事，artifact 留数据给本地，邮件做信令，本地做最后一跳。**

## workflow.yaml 结构

```yaml
name: my-project
trigger:
  schedule: "30 23 * * *"        # UTC，北京时间 07:30

email:                            # ← 原来是 bridge.email，现在顶层
  triggers:
    - subject: "✅ my-project"    # 匹配 GHA notify/email 的 subject

steps:
  # ═══ GHA 步骤（所有能云端做的都放这） ═══
  - id: step-name
    runner: gha
    capability: detect         # detect / collect / process
    using: script              # script / http / llm
    config:
      file: scripts/xxx.sh

  - id: sync
    runner: gha
    capability: store
    using: rclone               # 同步到云盘，人看
    config:
      remote: "jianguoyun"
      type: "webdav"
      url: "https://dav.jianguoyun.com/dav/"
      vendor: "other"
      user_secret: "RCLONE_USER"
      pass_secret: "RCLONE_PASS"
      source: "data/"
      target: "notebook/目标目录/"

  - id: notify
    runner: gha
    capability: notify
    using: email                # 信令
    config:
      to: "zhenchao@qq.com"
      subject: "✅ my-project"

  # ═══ Local 步骤（GHA 处理不了的放这） ═══
  - id: consume
    runner: local
    capability: consume
    using: script
    config:
      file: scripts/consume-local.sh   # 自己下载 artifact + 消费

  - id: notify-wechat
    runner: local
    capability: notify
    using: hermes
    config:
      message: "✅ 今日任务完成"
```

## 数据通路

```
GHA 内 data/*.json
  ├─ store/rclone → 坚果云 (人直接看)
  └─ upload-artifact → GitHub Artifact (机器用)
                              ↓
                    Local consume 脚本
                    gh run download → 处理
```

**关键：** 不需要 Git 桥，不需要 `bridge.repo`，不需要 `pull()`。

## 本地消费脚本模式

### 从 artifact 获取数据

```bash
#!/bin/bash
# scripts/consume-local.sh

REPO="sunzcdev/ai-daily-learning"
WORKFLOW="ai-daily-learning"
LWF_DIR="$HOME/.lwf/artifacts/ai-daily-learning"

# 找到最新成功的 workflow run
RUN_ID=$(gh run list --repo "$REPO" \
  --workflow "$WORKFLOW" --status success --limit 1 \
  --json databaseId --jq '.[0].databaseId')

if [ -z "$RUN_ID" ]; then
  echo "  ! 没有成功的 workflow run"
  exit 0
fi

# 下载 artifact（先清理旧文件，gh run download 不支持覆盖）
rm -rf "$LWF_DIR"
mkdir -p "$LWF_DIR"
gh run download "$RUN_ID" --repo "$REPO" --dir "$LWF_DIR"

# 消费数据
python3 scripts/write-obsidian.py
```

### 注意事项

- `gh run download` 不支持覆盖已有文件，**必须先 `rm -rf`**
- artifact 文件直接放在目标目录下，不是 `data/` 子目录
- 建议用 `--status success` 过滤，只消费成功的运行

## 部署流程

```bash
# 1. 写 workflow.yaml（参考上面的结构）
# 2. 生成 .github/workflows/ + lwf/runners/ + watchdog.d/
lwf deploy workflow.yaml

# 3. 修复 GHA workflow（因为 LWF generator 的 process/llm 不支持 system_prompt）
#    → 参考下面"GHA workflow 手写优化"章节

# 4. 配置本地 IMAP
vim ~/.lwf/watchdog.yaml       # IMAP 账号密码

# 5. 启动邮箱看门狗
lwf watchdog start              # 或 lwf watchdog once 单次轮询

# 6. 推送到 GitHub
git add -A && git commit -m "add workflow"
git push

# 7. 在 GitHub 仓库配置 Secrets
gh secret set LLM_KEY          -R <repo>      # LLM API Key
gh secret set RCLONE_USER      -R <repo>      # 坚果云账号
gh secret set RCLONE_PASS      -R <repo>      # 坚果云密码
gh secret set EMAIL_FROM       -R <repo>      # 发件邮箱
gh secret set EMAIL_PASS       -R <repo>      # 邮箱 SMTP 密码
```

## GHA workflow 手写优化

LWF 的 `process/llm` generator 功能有限（不支持 `system_prompt` + `input` 文件注入），
建议实际运行时用手写优化的版本。关键点：

### system_prompt 通过 env 变量

```yaml
- name: generate · process/llm
  id: generate
  env:
    SYSTEM_PROMPT: ${{ vars.SYSTEM_PROMPT }}
  run: |
    cat scripts/generate-prompt.txt > /tmp/prompt.txt
    cat data/fetch.json >> /tmp/prompt.txt
    echo "$SYSTEM_PROMPT" > /tmp/system.txt
    messages=$(jq -n \
      --arg sys "$(cat /tmp/system.txt)" \
      --arg usr "$(cat /tmp/prompt.txt)" \
      '{"model":"gpt-4o","messages":[{"role":"system","content":$sys},{"role":"user","content":$usr}],"max_tokens":12000}')
    curl -s -o data/generate.json \
      "https://models.github.ai/inference/v1/chat/completions" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer ${{ secrets.LLM_KEY }}" \
      -d "$messages"
```

### 不要 BRIDGE_REPO checkout

```yaml
# ✅ 直接 checkout 自己，不用桥仓库
- uses: actions/checkout@v4

# ❌ 旧版（桥仓库模式）不需要了
# - uses: actions/checkout@v4
#   with:
#     repository: ${{ secrets.BRIDGE_REPO || github.repository }}
```

### probe-output + artifact (LWF 自动生成，保留)

```yaml
- name: probe-output
  id: probe-output
  run: |
    FOUND=false
    for f in data/*.json; do
      [ -f "$f" ] && [ -s "$f" ] && FOUND=true && break
    done
    echo "has_output=$FOUND" >> $GITHUB_OUTPUT

- uses: actions/upload-artifact@v4
  if: steps.probe-output.outputs.has_output == 'true'
  with:
    name: my-project-${{ github.run_id }}
    path: data/
    retention-days: 3
```

## 完整示例项目

参见 `subprojects/ai-daily-learning/`（实际在 github.com/sunzcdev/ai-daily-learning）。

关键文件：
- `workflow.yaml` — 子项目定义
- `scripts/notify-email.py` — 邮件通知
- `scripts/consume-local.sh` — artifact 下载 + 消费
- `.github/workflows/ai-daily-learning.yml` — GHA 手写优化版
- `lwf/runners/ai-daily-learning_local.py` — LWF 生成的 Local Runner
