"""ログ設定ユーティリティ。[LEVEL][Tag] message 形式で統一する。"""
from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path


def setup(log_dir: str, mode: str, target_date: str) -> logging.Logger:
    """ファイル + コンソール両方に出力するロガーを構成する。"""
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_path / f"batch_{target_date}_{mode}_{ts}.log"

    fmt = "[%(levelname)s][%(name)s] %(message)s"
    logging.basicConfig(
        level=logging.INFO,
        format=fmt,
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    logger = logging.getLogger("pipeline")
    logger.info("batch_start mode=%s target_date=%s log_file=%s", mode, target_date, log_file)
    return logger
