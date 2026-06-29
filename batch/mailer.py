"""障害発生時のエラー通知メール送信。"""
from __future__ import annotations

import logging
import smtplib
import time
from email.mime.text import MIMEText
from typing import List

logger = logging.getLogger(__name__)


def send_error(
    *,
    smtp_host: str,
    smtp_port: int,
    username: str,
    password: str,
    mail_from: str,
    to: List[str],
    mode: str,
    target_date: str,
    failed_step: str,
    error_message: str,
    log_file: str,
    retry_count: int = 2,
    retry_interval_sec: int = 30,
) -> None:
    """エラー通知メールを送信する。失敗してもパイプラインは継続する。"""
    if not to:
        logger.warning("[mailer] 送信先が未設定のためメール通知をスキップします")
        return

    subject = f"[keiba-ai] バッチエラー: {mode} / {target_date} / {failed_step}"
    body = (
        f"実行日時: {_now()}\n"
        f"実行モード: {mode}\n"
        f"対象日: {target_date}\n"
        f"失敗ステップ: {failed_step}\n"
        f"エラー内容:\n{error_message}\n\n"
        f"ログファイル: {log_file}\n"
        f"再実行要否: 手動確認してください\n"
    )

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = mail_from
    msg["To"] = ", ".join(to)

    for attempt in range(1, retry_count + 1):
        try:
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.ehlo()
                server.starttls()
                server.login(username, password)
                server.sendmail(mail_from, to, msg.as_string())
            logger.info("[mailer] エラー通知メールを送信しました: %s", to)
            return
        except Exception as exc:
            logger.warning("[mailer] メール送信失敗 attempt=%d: %s", attempt, exc)
            if attempt < retry_count:
                time.sleep(retry_interval_sec)

    logger.error("[mailer] メール送信が全試行で失敗しました")


def _now() -> str:
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
