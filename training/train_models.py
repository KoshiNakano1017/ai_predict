"""LightGBM モデルの学習スクリプト。

バックフィルで生成した features.parquet を学習・検証データとして使用する。
時系列分割でデータを分割し、学習/バリデーション/テストを行う。

使い方:
  python training/train_models.py --data-dir C:\\keiba-ai\\runs --output-dir C:\\keiba-ai\\inference\\models
"""
from __future__ import annotations

import argparse
import logging
import pickle
import sys
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from inference.run_inference import FEATURE_COLS

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# --- 時系列分割 (11_特徴量設計.md §9) ---
TRAIN_UNTIL = "20221231"    # 〜2022年 で学習
VALID_FROM  = "20230101"    # 2023年 をバリデーション
TEST_FROM   = "20240101"    # 2024年以降 をテスト (一切学習に使わない)

TARGETS = {
    "is_win":  "lgbm_win_v1.pkl",
    "is_top2": "lgbm_top2_v1.pkl",
    "is_top3": "lgbm_top3_v1.pkl",
}

LGB_PARAMS = {
    "objective": "binary",
    "metric": "auc",
    "boosting_type": "gbdt",
    "num_leaves": 63,
    "learning_rate": 0.05,
    "feature_fraction": 0.8,
    "bagging_fraction": 0.8,
    "bagging_freq": 5,
    "min_child_samples": 20,
    "n_estimators": 1000,
    "random_state": 42,
    "verbose": -1,
}


def load_features(data_dir: str) -> pd.DataFrame:
    """runs/ 配下の全 features.parquet を結合して返す。"""
    base = Path(data_dir)
    files = sorted(base.glob("*/features.parquet"))
    if not files:
        raise FileNotFoundError(f"features.parquet が見つかりません: {base}")

    dfs = [pd.read_parquet(f) for f in files]
    df = pd.concat(dfs, ignore_index=True)
    logger.info("学習データ: %d 行 (ファイル数: %d)", len(df), len(files))
    return df


def split_data(df: pd.DataFrame):
    """race_key の先頭8桁 (YYYYMMDD) で時系列分割する。"""
    df = df.copy()
    df["_date"] = df["race_key"].str[:8]

    train = df[df["_date"] <= TRAIN_UNTIL]
    valid = df[(df["_date"] >= VALID_FROM) & (df["_date"] < TEST_FROM)]
    test  = df[df["_date"] >= TEST_FROM]

    logger.info("train: %d / valid: %d / test: %d", len(train), len(valid), len(test))
    return train, valid, test


def make_target(df: pd.DataFrame, target: str) -> pd.Series:
    if target == "is_win":
        return (df["finish_position"] == 1).astype(int)
    elif target == "is_top2":
        return (df["finish_position"] <= 2).astype(int)
    elif target == "is_top3":
        return (df["finish_position"] <= 3).astype(int)
    raise ValueError(f"未知のターゲット: {target}")


def train_one(train, valid, test, target: str, output_dir: str) -> None:
    """1つのターゲットに対してモデルを学習・評価・保存する。

    モデルと一緒に学習時に使用した feature_cols も保存する。
    推論時に列数が不一致になるのを防ぐため、推論側はこの feature_cols
    に従って入力を構築する。
    """
    feat_cols = [c for c in FEATURE_COLS if c in train.columns]

    X_train, y_train = train[feat_cols], make_target(train, target)
    X_valid, y_valid = valid[feat_cols], make_target(valid, target)
    X_test,  y_test  = test[feat_cols],  make_target(test,  target)

    # 欠損を除外してから train
    mask = y_train.notna()
    X_train, y_train = X_train[mask], y_train[mask]

    model = lgb.LGBMClassifier(**LGB_PARAMS)
    model.fit(
        X_train, y_train,
        eval_set=[(X_valid, y_valid)],
        callbacks=[lgb.early_stopping(50), lgb.log_evaluation(100)],
    )

    # バリデーション AUC
    val_auc = roc_auc_score(y_valid[y_valid.notna()], model.predict_proba(X_valid[y_valid.notna()])[:, 1])
    test_auc = roc_auc_score(y_test[y_test.notna()], model.predict_proba(X_test[y_test.notna()])[:, 1])
    logger.info("[%s] valid_auc=%.4f test_auc=%.4f", target, val_auc, test_auc)

    # 保存（モデル本体と feature_cols をセットで pickle）
    out = Path(output_dir) / TARGETS[target]
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "wb") as f:
        pickle.dump({"model": model, "feature_cols": feat_cols}, f)
    logger.info("[%s] モデル保存: %s (features=%d)", target, out, len(feat_cols))


def main() -> None:
    p = argparse.ArgumentParser(description="LightGBM モデル学習")
    p.add_argument("--data-dir", required=True)
    p.add_argument("--output-dir", required=True)
    args = p.parse_args()

    df = load_features(args.data_dir)
    train, valid, test = split_data(df)

    for target in TARGETS:
        logger.info("=== %s の学習開始 ===", target)
        train_one(train, valid, test, target, args.output_dir)

    logger.info("全モデル学習完了")


if __name__ == "__main__":
    main()
