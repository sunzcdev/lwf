#!/usr/bin/env python3
"""ai-briefing 采集脚本 — LWF 子项目调用

多源采集：GitHub 搜索 + Trending + Hacker News + Reddit + TopHub
输出：data/collect.json（统一 LWF 格式）
"""
import sys, os, json
from datetime import datetime

# 将 ai-briefing 源码目录加入路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'ai-briefing'))

from src.collector.ai_briefing_collector import collect_projects, collect_news, _dedup
from src.config import DATA_DIR

mode = sys.argv[1] if len(sys.argv) > 1 else 'daily'

projects = collect_projects(mode)
news = collect_news(mode)
all_items = _dedup(projects + [n for n in news if n.get('_kind') != 'noise'])

# LWF 统一格式输出
output = {
    "workflow": "ai-briefing",
    "step_id": "collect",
    "timestamp": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
    "data": {
        "projects": projects,
        "news": news,
        "mode": mode,
        "total": len(all_items)
    },
    "meta": {"runner": "gha", "status": "success"}
}

os.makedirs('data', exist_ok=True)
with open('data/collect.json', 'w') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"[lwf] 采集完成: {len(projects)} 项目, {len(news)} 新闻")
