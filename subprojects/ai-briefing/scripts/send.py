#!/usr/bin/env python3
"""ai-briefing 渲染 + 发信脚本 — LWF 子项目调用

读取 data/digest.json（LLM 精选结果），生成 HTML，通过 QQ SMTP 发送
"""
import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'ai-briefing'))

# 读取 LLM 精选结果
digest_path = 'data/digest.json'
if not os.path.exists(digest_path):
    print("[lwf] 无精选结果，跳过发信")
    sys.exit(0)

with open(digest_path) as f:
    digest = json.load(f)

# 渲染 HTML（复用 ai-briefing 的模板和渲染逻辑）
from src.digest.send_ai_briefing import send
from src.config import QQ_SMTP_PASS, DEFAULT_TO_EMAIL

to_email = os.environ.get('EMAIL_TO', DEFAULT_TO_EMAIL)
subject = f"AI 新玩意简报 {datetime.now().strftime('%Y-%m-%d')}"

# 简单渲染：从 digest 数据构建 HTML
news = digest.get('data', {}).get('news', [])
projects = digest.get('data', {}).get('projects', [])

html_parts = ['<h2>精选项目</h2>']
for p in projects:
    html_parts.append(f'<p><b>{p.get("name","")}</b> — {p.get("comment","")}</p>')

if news:
    html_parts.append('<h2>热点事件</h2>')
    for n in news:
        html_parts.append(f'<p><b>{n.get("name","")}</b> — {n.get("comment","")}</p>')

html = '<html><body>' + ''.join(html_parts) + '</body></html>'

try:
    send(html, subject, to_email)
    print(f"[lwf] 邮件已发送至 {to_email}")
except Exception as e:
    print(f"[lwf] 发信失败: {e}")
