"""IMAP 邮箱看门狗 — 检测通知邮件 → 触发 Local Runner

配置分两层：

1. **全局 IMAP 配置** `~/.lwf/watchdog.yaml`::

        imap:
          host: imap.qq.com
          port: 993
          user: zhenchao@example.com
          pass: xxxxxx

2. **子项目 trigger 配置** `~/.lwf/watchdog.d/{name}.yaml`::

        # 由 lwf deploy 自动生成
        runner: ~/.lwf/runners/ai-daily-learning_local.py
        triggers:
          - subject: "✅ ai-daily-learning"
"""

import glob
import imaplib
import logging
import os
import subprocess
import time

logger = logging.getLogger("lwf.watchdog.email")


class EmailWatchdog:
    """IMAP-based email watcher that triggers Local Runners.

    IMAP 凭证来自全局配置文件；trigger→runner 映射来自
    ``watchdog.d/`` 目录（由 ``lwf deploy`` 按子项目生成）。
    """

    def __init__(self, config_path="~/.lwf/watchdog.yaml"):
        self._load_global_config(config_path)
        self._load_triggers_from_d()

    # ── 加载配置 ──

    def _load_global_config(self, config_path):
        import yaml
        path = os.path.expanduser(config_path)
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"看门狗全局配置不存在: {path}\n"
                f"请创建该文件，填入 IMAP 账号信息。"
            )
        with open(path) as f:
            cfg = yaml.safe_load(f) or {}
        self.imap = cfg.get("imap", {})
        missing = [k for k in ("host", "user", "pass") if k not in self.imap]
        if missing:
            raise ValueError(f"IMAP 配置缺少字段: {missing}")

    def _load_triggers_from_d(self):
        """扫描 ``~/.lwf/watchdog.d/*.yaml``，合并所有 trigger。"""
        import yaml
        d_path = os.path.expanduser("~/.lwf/watchdog.d")
        self.triggers = []
        if not os.path.isdir(d_path):
            logger.info("watchdog.d/ 不存在，无 trigger")
            return
        for fp in sorted(glob.glob(os.path.join(d_path, "*.yaml"))):
            with open(fp) as f:
                sub_cfg = yaml.safe_load(f) or {}
            runner = sub_cfg.get("runner", "")
            for t in sub_cfg.get("triggers", []):
                self.triggers.append({
                    "subject": t["subject"],
                    "runner": os.path.expanduser(runner),
                })
        logger.info(f"已加载 {len(self.triggers)} 个 trigger (来自 {len(os.listdir(d_path))} 个文件)")

    # ── 轮询 ──

    def poll_once(self):
        """连接 IMAP，检查未读邮件，匹配 trigger 则执行 runner。"""
        conn = self._connect()
        try:
            conn.select("INBOX")
            for t in self.triggers:
                self._match_and_run(conn, t["subject"], t["runner"])
        finally:
            conn.logout()

    def run_forever(self, interval=60):
        """每隔 interval 秒轮询一次。"""
        logger.info(f"Email watchdog 启动，轮询间隔 {interval}s")
        while True:
            try:
                self.poll_once()
            except Exception:
                logger.exception("轮询异常，继续下一轮")
            time.sleep(interval)

    # ── 内部 ──

    def _connect(self):
        conn = imaplib.IMAP4_SSL(self.imap["host"], self.imap.get("port", 993))
        conn.login(self.imap["user"], self.imap["pass"])
        return conn

    def _match_and_run(self, conn, subject, runner_path):
        status, data = conn.search(None, f'(UNSEEN SUBJECT "{subject}")')
        if status != "OK":
            return
        nums = data[0].split() if data[0] else []
        for num in nums:
            logger.info(f"📧 匹配 trigger [{subject}] → {runner_path}")
            self._run_runner(runner_path)
            conn.store(num, "+FLAGS", "\\Seen")

    def _run_runner(self, path):
        if not os.path.exists(path):
            logger.warning(f"Runner 不存在: {path}")
            return
        result = subprocess.run(
            ["python3", path],
            capture_output=True, text=True, timeout=300,
        )
        out = result.stdout.strip()[:500]
        err = result.stderr.strip()[:500]
        logger.info(f"  exit={result.returncode}")
        if out:
            logger.info(f"  > {out}")
        if err:
            logger.warning(f"  ! {err}")
