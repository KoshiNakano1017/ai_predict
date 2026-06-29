"""race_key / entry_key の生成と検証。

race_key  = 開催年(4) + 開催月日(4) + 競馬場コード(2) + 開催回(2) + 開催日目(2) + レース番号(2)  = 16桁
entry_key = race_key(16) + 馬番(2) = 18桁

>> 実際の列名・桁数は CrossFactor SQLite の実データで確認が必要。
   CrossFactor SQLite パスは config.yaml で設定する。
"""
from __future__ import annotations

import re
from typing import Optional


RACE_KEY_RE = re.compile(r"^\d{16}$")
ENTRY_KEY_RE = re.compile(r"^\d{18}$")


def build_race_key(
    kai_nen: str | int,    # 開催年 (YYYY)
    kai_tsuki_hi: str | int,  # 開催月日 (MMDD)
    keibajo: str | int,    # 競馬場コード (2桁)
    kai: str | int,        # 開催回 (2桁)
    nichi_me: str | int,   # 開催日目 (2桁)
    race_no: str | int,    # レース番号 (2桁)
) -> str:
    """race_key を生成して返す。"""
    key = (
        f"{int(kai_nen):04d}"
        f"{str(kai_tsuki_hi).zfill(4)}"
        f"{str(keibajo).zfill(2)}"
        f"{str(kai).zfill(2)}"
        f"{str(nichi_me).zfill(2)}"
        f"{str(race_no).zfill(2)}"
    )
    assert RACE_KEY_RE.match(key), f"不正な race_key: {key!r}"
    return key


def build_entry_key(race_key: str, uma_ban: str | int) -> str:
    """entry_key を生成して返す。"""
    key = f"{race_key}{str(uma_ban).zfill(2)}"
    assert ENTRY_KEY_RE.match(key), f"不正な entry_key: {key!r}"
    return key


def validate_race_key(key: str) -> bool:
    return bool(RACE_KEY_RE.match(key))


def validate_entry_key(key: str) -> bool:
    return bool(ENTRY_KEY_RE.match(key))


def race_key_to_parts(race_key: str) -> dict:
    """race_key を構成要素に分解する（デバッグ用）。"""
    assert validate_race_key(race_key), f"不正な race_key: {race_key!r}"
    return {
        "kai_nen": race_key[0:4],
        "kai_tsuki_hi": race_key[4:8],
        "keibajo": race_key[8:10],
        "kai": race_key[10:12],
        "nichi_me": race_key[12:14],
        "race_no": race_key[14:16],
    }
