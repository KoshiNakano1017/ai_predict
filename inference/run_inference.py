"""LightGBM 推論スクリプト。

学習済みモデルを使って各馬の勝率・連対率・複勝率・期待値を算出する。
推論失敗時はベースデータを保持し、予測結果のみ未更新として通知する。
"""
from __future__ import annotations

import logging
import pickle
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# --- Phase 1 MVP で使う特徴量列 (11_特徴量設計.md §5 準拠) ---
FEATURE_COLS = [
    # A. レース条件系
    "race_distance", "track_type", "track_condition", "weather",
    "num_horses", "race_class_code", "straight_distance",
    # B. 馬の能力系
    "avg_finish_3", "avg_finish_5", "avg_popularity_3",
    "place_rate_track", "place_rate_course", "place_rate_distance",
    "win_recovery_rate", "place_recovery_rate",
    "frame_number", "horse_number", "horse_weight", "horse_weight_diff",
    "carrying_weight", "rest_weeks", "runs_since_return", "distance_change",
    "horse_age", "horse_sex",
    # C. CrossFactor 独自系
    "position_index", "position_index_rank", "predicted_running_style",
    "top5_4c_rate", "top3_finish_rate", "pci",
    "turn_aptitude", "weight_correction", "weight_correction_finish",
    "user_index_1",
    # D. 騎手・調教師系
    "jockey_win_rate_all", "jockey_win_rate_course", "trainer_win_rate_all",
    "jockey_change",
    # E. 調教系
    "slope_1_4f", "slope_1_1f", "slope_2_4f",
    "wood_1_4f", "wood_1_1f",
    # F. オッズ・市場系
    "win_odds", "popularity_rank", "place_odds_low", "place_odds_high",
]


def _load_model_bundle(model_path: str):
    """pickle を読み、(model, feature_cols) を返す。

    新形式: {"model": ..., "feature_cols": [...]} がそのまま入っている
    旧形式: モデル本体だけが入っている → feature_cols は FEATURE_COLS をフォールバック
    """
    with open(model_path, "rb") as f:
        loaded = pickle.load(f)
    if isinstance(loaded, dict) and "model" in loaded:
        return loaded["model"], loaded.get("feature_cols", FEATURE_COLS)
    return loaded, FEATURE_COLS


def run(
    df_entries: pd.DataFrame,
    model_dir: str,
    win_model_name: str,
    top2_model_name: str,
    top3_model_name: str,
) -> Optional[pd.DataFrame]:
    """推論を実行して entry_key + 各予測値の DataFrame を返す。

    モデルが見つからない、または推論に失敗した場合は None を返す。
    """
    model_path_win = Path(model_dir) / win_model_name
    model_path_top2 = Path(model_dir) / top2_model_name
    model_path_top3 = Path(model_dir) / top3_model_name

    for path in [model_path_win, model_path_top2, model_path_top3]:
        if not path.exists():
            logger.error("[inference] モデルファイルが見つかりません: %s", path)
            return None

    try:
        model_win, feat_cols_win = _load_model_bundle(str(model_path_win))
        model_top2, feat_cols_top2 = _load_model_bundle(str(model_path_top2))
        model_top3, feat_cols_top3 = _load_model_bundle(str(model_path_top3))
    except Exception as exc:
        logger.error("[inference] モデル読込失敗: %s", exc)
        return None

    def _build_X(feat_cols):
        """学習時の feature_cols に合わせて入力 DataFrame を組み立てる。

        df_entries に存在しない列は 0 で補完。
        余分な列は除外する（学習時にモデルが見ていない列は渡さない）。
        """
        X = df_entries.copy()
        for col in feat_cols:
            if col not in X.columns:
                X[col] = 0
        return X[feat_cols]

    try:
        # 各モデルの学習時 feature_cols に揃えた入力で推論
        raw_win = model_win.predict_proba(_build_X(feat_cols_win))[:, 1]
        raw_top2 = model_top2.predict_proba(_build_X(feat_cols_top2))[:, 1]
        raw_top3 = model_top3.predict_proba(_build_X(feat_cols_top3))[:, 1]
    except Exception as exc:
        logger.error("[inference] 推論実行失敗: %s", exc)
        return None

    df_result = df_entries[["entry_key", "race_key", "horse_number",
                             "win_odds", "place_odds_low", "popularity_rank"]].copy()

    # race_key ごとに確率を正規化して確率の整合性を保つ
    df_result["_raw_win"] = raw_win
    df_result["_raw_top2"] = raw_top2
    df_result["_raw_top3"] = raw_top3

    results = []
    for race_key, grp in df_result.groupby("race_key"):
        grp = grp.copy()
        # 正規化: 各レース内の合計が 1 に近づくよう calibrate
        win_sum = grp["_raw_win"].sum()
        top2_sum = grp["_raw_top2"].sum()
        top3_sum = grp["_raw_top3"].sum()

        grp["win_rate"] = (grp["_raw_win"] / win_sum * 100).clip(0, 100).round(1) if win_sum else 0
        grp["place_rate"] = (grp["_raw_top2"] / top2_sum * 100).clip(0, 100).round(1) if top2_sum else 0
        grp["show_rate"] = (grp["_raw_top3"] / top3_sum * 100).clip(0, 100).round(1) if top3_sum else 0

        # 期待値 = 予想勝率(小数) × 単勝オッズ / 予想複勝率(小数) × 複勝オッズ下限
        grp["expected_value_win"] = (
            (grp["win_rate"] / 100) * grp["win_odds"].fillna(0)
        ).round(3)
        grp["expected_value_place"] = (
            (grp["show_rate"] / 100) * grp["place_odds_low"].fillna(0)
        ).round(3)

        results.append(grp)

    df_pred = pd.concat(results, ignore_index=True)
    logger.info("[inference] 推論完了: %d 頭", len(df_pred))
    return df_pred


def assign_star_ratings(
    df_pred: pd.DataFrame,
    star_ev_threshold: float = 1.05,
    triangle_ev_threshold: float = 1.02,
    longshot_popularity_rank: int = 5,
    risky_favorite_rank: int = 3,
) -> pd.DataFrame:
    """各馬に star_rating (★/▲/⚠/◆) を割り当てる。

    ★: 期待値が最も高い本命
    ▲: 2番目に期待値が高い対抗
    ⚠: 人気上位 (3位以内) だが期待値が低い危険な人気馬
    ◆: 人気薄 (5位以下) で期待値が高い穴馬
    """
    df = df_pred.copy()
    df["star_rating"] = None

    for race_key, grp in df.groupby("race_key"):
        idx = grp.index
        ev = grp["expected_value_win"].fillna(0)
        pop = grp["popularity_rank"].fillna(99)

        # ★: 期待値最大の馬
        star_idx = ev.idxmax()
        df.loc[star_idx, "star_rating"] = "★"

        # ▲: ★以外で期待値2位
        remaining = ev.drop(star_idx)
        if not remaining.empty:
            triangle_idx = remaining.idxmax()
            df.loc[triangle_idx, "star_rating"] = "▲"

        # ⚠: 人気上位で期待値がしきい値未満
        risky = idx[(pop <= risky_favorite_rank) & (ev < triangle_ev_threshold)]
        for i in risky:
            if df.loc[i, "star_rating"] is None:
                df.loc[i, "star_rating"] = "⚠"

        # ◆: 人気薄で期待値がしきい値以上
        longshots = idx[(pop >= longshot_popularity_rank) & (ev >= star_ev_threshold)]
        for i in longshots:
            if df.loc[i, "star_rating"] is None:
                df.loc[i, "star_rating"] = "◆"

    return df
