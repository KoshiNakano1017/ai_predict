"""欠損補完・型変換・カテゴリエンコーディング。"""
from __future__ import annotations

import logging
from datetime import date

import pandas as pd

logger = logging.getLogger(__name__)

# LightGBM は正規化不要。カテゴリ列だけ Label Encoding する。

RUNNING_STYLE_MAP = {"逃": 1, "先": 2, "差": 3, "追": 4}
TRACK_CONDITION_MAP = {"良": 0, "稍重": 1, "重": 2, "不良": 3}
TRACK_TYPE_MAP = {"芝": 0, "ダート": 1, "障害": 2}
SEX_MAP = {"牡": 0, "牝": 1, "騸": 2}


# SQLite から取得した値は基本 TEXT のため、特徴量計算前に数値化する必要がある。
# 該当列が string のまま fill_missing/mean() に渡ると TypeError になる。
NUMERIC_COLUMNS = [
    # 過去成績
    "avg_finish_3", "avg_finish_5", "avg_popularity_3",
    # 適性
    "place_rate_track", "place_rate_course", "place_rate_distance", "turn_aptitude",
    # ペース・指数
    "position_index", "position_index_rank",
    "top5_4c_rate", "top3_finish_rate", "pci",
    # 状態
    "rest_weeks", "runs_since_return", "distance_change",
    "weight_correction", "weight_correction_finish",
    "win_recovery_rate", "place_recovery_rate",
    # 調教（坂路・ウッド）
    "slope_1_4f", "slope_1_1f", "slope_2_4f", "wood_1_4f", "wood_1_1f",
    # ユーザー指数
    "user_index_1", "user_index_2", "user_index_3",
    # 結果（バックフィル時のみ存在）
    "finish_position",
    # 馬の物理量
    "carrying_weight", "horse_weight", "horse_weight_diff",
    # 番号系
    "frame_number", "horse_number",
]


def coerce_numeric(df: pd.DataFrame) -> pd.DataFrame:
    """数値特徴量列を float / Int64 に変換する。空文字や非数値は NaN に倒す。

    SQLite から取得した値は基本 TEXT のため、特徴量計算前に必ず通すこと。
    """
    df = df.copy()
    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def fill_missing(df: pd.DataFrame) -> pd.DataFrame:
    """欠損値を列種別に応じて補完する。

    NOTE: 呼び出し前に coerce_numeric() を通しておくこと
    （未通の場合でも安全側で内部で再度 coerce する）。
    """
    df = coerce_numeric(df)

    # 調教なし: -999 で埋め + フラグ追加
    training_cols = ["slope_1_4f", "slope_1_1f", "slope_2_4f", "wood_1_4f", "wood_1_1f"]
    for col in training_cols:
        if col in df.columns:
            df[f"{col}_missing"] = df[col].isna().astype(int)
            df[col] = df[col].fillna(-999)
            missing_count = df[f"{col}_missing"].sum()
            if missing_count:
                logger.info("[normalizer] missing_training col=%s count=%d", col, missing_count)

    # デビュー戦 (過去実績なし): 平均値または初出走フラグで対応
    for col in ["avg_finish_3", "avg_finish_5", "avg_popularity_3"]:
        if col in df.columns:
            mean_val = df[col].mean()
            df["is_debut"] = df[col].isna().astype(int)
            df[col] = df[col].fillna(mean_val if pd.notna(mean_val) else 8.0)

    # 適性スコア・回収率の欠損: 0 で補完
    for col in ["place_rate_track", "place_rate_course", "place_rate_distance",
                "win_recovery_rate", "place_recovery_rate", "turn_aptitude"]:
        if col in df.columns:
            df[col] = df[col].fillna(0)

    return df


def encode_categoricals(df: pd.DataFrame) -> pd.DataFrame:
    """カテゴリ変数を LightGBM 用の整数値に変換する。"""
    df = df.copy()

    if "predicted_running_style" in df.columns:
        df["predicted_running_style"] = (
            df["predicted_running_style"].map(RUNNING_STYLE_MAP).fillna(0).astype(int)
        )

    if "track_condition" in df.columns:
        df["track_condition"] = (
            df["track_condition"].map(TRACK_CONDITION_MAP).fillna(0).astype(int)
        )

    if "track_type" in df.columns:
        df["track_type"] = (
            df["track_type"].map(TRACK_TYPE_MAP).fillna(0).astype(int)
        )

    if "horse_sex" in df.columns:
        df["horse_sex"] = (
            df["horse_sex"].map(SEX_MAP).fillna(0).astype(int)
        )

    return df


def calc_horse_age(df: pd.DataFrame, race_date: str) -> pd.DataFrame:
    """birth_date (YYYYMMDD) と race_date (YYYY-MM-DD) から馬齢を算出する。"""
    df = df.copy()
    if "birth_date" not in df.columns:
        return df
    try:
        rd = date.fromisoformat(race_date)
        def age(bday: str) -> int | None:
            try:
                b = date(int(str(bday)[:4]), int(str(bday)[4:6]), int(str(bday)[6:8]))
                return (rd - b).days // 365
            except Exception:
                return None
        df["horse_age"] = df["birth_date"].map(age)
    except Exception as exc:
        logger.warning("[normalizer] horse_age 計算失敗: %s", exc)
    return df
