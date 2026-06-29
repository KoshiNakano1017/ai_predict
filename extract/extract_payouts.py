"""JV払戻 から払戻データを抽出する (バックテスト・学習用)。"""
from __future__ import annotations

import logging
from typing import List

import pandas as pd

from extract.sqlite_client import query_to_df

logger = logging.getLogger(__name__)

TABLE = "JV払戻"


def extract(conn, race_keys: List[str], df_races: pd.DataFrame) -> pd.DataFrame:
    """対象 race_key の払戻情報を抽出する。"""
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
        """
        params = (year, mmdd, keibajo, kai, nichi_me, race_no)
        raw = query_to_df(conn, sql, params)

        if raw.empty:
            continue

        for _, row in raw.iterrows():
            all_rows.append({
                "race_key": race_key,
                "win_payout": row.get("単勝払戻"),
                "place_payout": row.get("複勝払戻"),
            })

    return pd.DataFrame(all_rows) if all_rows else pd.DataFrame()
