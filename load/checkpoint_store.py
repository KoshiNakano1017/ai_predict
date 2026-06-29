"""差分更新のチェックポイント管理。ローカルファイルに JSON で保存する。"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Set

logger = logging.getLogger(__name__)


class CheckpointStore:
    def __init__(self, checkpoint_file: str) -> None:
        self._path = Path(checkpoint_file)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._data: dict = self._load()

    def _load(self) -> dict:
        if self._path.exists():
            with open(self._path, encoding="utf-8") as f:
                return json.load(f)
        return {
            "last_run_at": None,
            "last_target_date": None,
            "processed_race_keys": [],
        }

    def _save(self) -> None:
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    def get_processed_keys(self) -> Set[str]:
        return set(self._data.get("processed_race_keys", []))

    def mark_done(self, race_keys: list[str], target_date: str) -> None:
        """処理済み race_key を記録する。"""
        existing = set(self._data.get("processed_race_keys", []))
        existing.update(race_keys)
        self._data["processed_race_keys"] = sorted(existing)
        self._data["last_run_at"] = datetime.now().isoformat()
        self._data["last_target_date"] = target_date
        self._save()
        logger.info("[checkpoint] %d 件の race_key を記録しました", len(race_keys))

    def reset_for_date(self, target_date: str) -> None:
        """指定日分のチェックポイントをリセットする (再実行用)。"""
        keys = self._data.get("processed_race_keys", [])
        # race_key の先頭8桁 (YYYYMMDD) で対象日を判別
        date_prefix = target_date.replace("-", "")
        remaining = [k for k in keys if not k.startswith(date_prefix)]
        removed = len(keys) - len(remaining)
        self._data["processed_race_keys"] = remaining
        self._save()
        logger.info("[checkpoint] %s 分の %d 件をリセットしました", target_date, removed)
