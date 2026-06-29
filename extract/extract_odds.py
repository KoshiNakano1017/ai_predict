"""JVオッズ_単複枠 からオッズを抽出する。"""
from __future__ import annotations

import logging
from typing import List

import pandas as pd

from extract.sqlite_client import query_to_df
from transform.feature_mapper import map_odds_columns, ODDS_COLUMN_MAP

logger = logging.getLogger(__name__)

TABLE = "JVオッズ_単複枠"


def extract(conn, race_keys: List[str], df_races: pd.DataFrame) -> pd.DataFrame:
    """対象 race_key の全時点オッズを抽出する。

    締め切り直前の選択は odds_selector.select_latest_odds() で行う。
    """
    if not race_keys:
        return pd.DataFrame()

    races_index = df_races.set_index("race_key") if "race_key" in df_races.columns else pd.DataFrame()

    all_rows = []
    for race_key in race_keys:
        if race_key not in races_index.index:
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
            ORDER BY 発表月日時分, 馬番
        """
        params = (year, mmdd, keibajo, kai, nichi_me, race_no)
        raw = query_to_df(conn, sql, params)

        if raw.empty:
            logger.warning("[extract_odds] オッズなし race_key=%s", race_key)
            continue

        for _, row in raw.iterrows():
            mapped = map_odds_columns(dict(row))
            mapped["race_key"] = race_key
            uma_ban = row.get("馬番", "")
            mapped["horse_number"] = int(str(uma_ban)) if uma_ban else None
            all_rows.append(mapped)

    if not all_rows:
        return pd.DataFrame()

    df = pd.DataFrame(all_rows)
    logger.info("[extract_odds] オッズ抽出: %d 行", len(df))
    return df
