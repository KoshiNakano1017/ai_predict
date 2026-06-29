"""transform/master_merger.py のユニットテスト。

JV馬毎レース情報EX に既に格納されている騎手名/調教師名を優先しつつ、
欠損している行のみマスタの値で埋めることを保証する。
"""
import pandas as pd
import numpy as np

from transform.master_merger import merge_master_name


def test_merge_master_name_fills_missing_only():
    """馬毎情報の jockey_name が欠損している行だけマスタ値で補完する。"""
    df_entries = pd.DataFrame({
        "entry_key": ["e1", "e2", "e3"],
        "jockey_code": ["J01", "J02", "J03"],
        "jockey_name": ["武豊", None, "ルメール"],
    })
    df_master = pd.DataFrame({
        "jockey_code": ["J01", "J02", "J03"],
        "jockey_name": ["MASTER_武豊", "MASTER_川田", "MASTER_ルメール"],
    })

    result = merge_master_name(df_entries, df_master, key="jockey_code", name_col="jockey_name")

    assert result.loc[0, "jockey_name"] == "武豊"             # 元の値が優先
    assert result.loc[1, "jockey_name"] == "MASTER_川田"      # 欠損のみマスタ値で補完
    assert result.loc[2, "jockey_name"] == "ルメール"
    assert "jockey_name_master" not in result.columns


def test_merge_master_name_when_entries_have_no_name_column():
    """馬毎情報に jockey_name 列が無くてもマスタから補完して列を追加する。"""
    df_entries = pd.DataFrame({
        "entry_key": ["e1"],
        "jockey_code": ["J01"],
    })
    df_master = pd.DataFrame({
        "jockey_code": ["J01"],
        "jockey_name": ["武豊"],
    })

    result = merge_master_name(df_entries, df_master, key="jockey_code", name_col="jockey_name")
    assert result.loc[0, "jockey_name"] == "武豊"


def test_merge_master_name_with_empty_master_is_noop():
    df_entries = pd.DataFrame({
        "entry_key": ["e1"],
        "trainer_code": ["T01"],
        "trainer_name": ["山田太郎"],
    })
    df_master = pd.DataFrame()

    result = merge_master_name(df_entries, df_master, key="trainer_code", name_col="trainer_name")
    assert result.equals(df_entries)


def test_merge_master_name_with_missing_key_column_is_noop():
    """entries 側に結合キーがない場合は何もしない。"""
    df_entries = pd.DataFrame({"entry_key": ["e1"]})
    df_master = pd.DataFrame({
        "trainer_code": ["T01"],
        "trainer_name": ["山田"],
    })

    result = merge_master_name(df_entries, df_master, key="trainer_code", name_col="trainer_name")
    assert result.equals(df_entries)


def test_merge_master_name_dedupes_master_rows():
    """マスタに同一キーが複数あっても出走馬が増えない (drop_duplicates)。"""
    df_entries = pd.DataFrame({
        "entry_key": ["e1", "e2"],
        "trainer_code": ["T01", "T02"],
        "trainer_name": [None, None],
    })
    df_master = pd.DataFrame({
        "trainer_code": ["T01", "T01", "T02"],
        "trainer_name": ["A", "A", "B"],
    })

    result = merge_master_name(df_entries, df_master, key="trainer_code", name_col="trainer_name")
    assert len(result) == 2
    assert result.loc[0, "trainer_name"] == "A"
    assert result.loc[1, "trainer_name"] == "B"
