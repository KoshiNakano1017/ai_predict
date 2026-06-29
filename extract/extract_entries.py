"""JV馬毎レース情報EX から出走馬情報を抽出し entry_key を付与する。"""
from __future__ import annotations

import logging
from typing import List

import pandas as pd

from extract.sqlite_client import query_to_df
from transform.key_builder import build_race_key, build_entry_key
from transform.feature_mapper import map_entry_columns

logger = logging.getLogger(__name__)

TABLE = "JV馬毎レース情報EX"


def extract(conn, race_keys: List[str], df_races: pd.DataFrame) -> pd.DataFrame:
    """対象 race_key の出走馬を抽出して entry_key を付与する。

    df_races は race_key -> (kai_nen, kai_tsuki_hi, ...) の参照に使用する。
    """
    if not race_keys:
        return pd.DataFrame()

    # race_key -> 元の key 部品を引けるようにしておく
    races_index = df_races.set_index("race_key") if "race_key" in df_races.columns else pd.DataFrame()

    all_rows = []
    for race_key in race_keys:
        if race_key not in races_index.index:
            logger.warning("[extract_entries] race_key %s が races に見つかりません", race_key)
            continue

        race = races_index.loc[race_key]
        year = str(race.get("kai_nen", ""))
        mmdd = str(race.get("kai_tsuki_hi", "")).zfill(4)
        keibajo = str(race.get("keibajo", "")).zfill(2)
        kai = str(race.get("kai", "")).zfill(2)
        nichi_me = str(race.get("nichi_me", "")).zfill(2)
        race_no = str(race.get("race_no", "")).zfill(2)

        sql = f"""
            SELECT *
            FROM [{TABLE}]
            WHERE 開催年 = ? AND 開催月日 = ? AND 競馬場 = ?
              AND 開催回 = ? AND 開催日目 = ? AND 番号 = ?
            ORDER BY 馬番
        """
        params = (year, mmdd, keibajo, kai, nichi_me, race_no)
        raw = query_to_df(conn, sql, params)

        if raw.empty:
            logger.warning("[extract_entries] 出走馬なし race_key=%s", race_key)
            continue

        for _, row in raw.iterrows():
            mapped = map_entry_columns(dict(row))
            mapped["race_key"] = race_key
            uma_ban = row.get("馬番", "")
            mapped["entry_key"] = build_entry_key(race_key, uma_ban)
            # 数値列は型を正規化（merge / sort で str <-> int 不整合が起きないように）
            try:
                mapped["horse_number"] = int(str(uma_ban)) if str(uma_ban) else None
            except (ValueError, TypeError):
                mapped["horse_number"] = None
            try:
                fn = mapped.get("frame_number")
                mapped["frame_number"] = int(str(fn)) if fn not in (None, "") else None
            except (ValueError, TypeError):
                mapped["frame_number"] = None
            all_rows.append(mapped)

        logger.info("[extract_entries] entries_extracted race_key=%s count=%d", race_key, len(raw))

    if not all_rows:
        return pd.DataFrame()

    df = pd.DataFrame(all_rows)
    logger.info("[extract_entries] 合計 entries=%d races=%d", len(df), len(race_keys))
    return df
