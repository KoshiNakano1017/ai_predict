# -*- coding: utf-8 -*-
"""features.parquet を水増しして疑似学習データを生成する（B 案：推論まで疎通させる用）。

目的:
  - train_models.py が要求する `runs/*/features.parquet` (時系列複数年分)
    を CrossFactor 受領前にダミー生成し、.pkl を一旦作る。
  - これにより batch/run_pipeline.py が **推論まで完走** できる状態に持ち込む。

データ生成方針:
  - 元 features.parquet を年×週の組み合わせで複製
  - race_key の先頭 8 桁 (YYYYMMDD) を新しい年月日に書き換え
  - finish_position を popularity_rank ベース + ノイズで生成
    （人気上位ほど好走しやすい弱い信号を学習対象に与える）
  - train: 2018-2022 / valid: 2023 / test: 2024  (train_models.py 既定値に合わせる)

注意:
  - これは「パイプライン疎通用」であり実用精度は出ない
  - CrossFactor 受領後は実データでバックフィル → 再学習が必要
"""
from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

import numpy as np
import pandas as pd

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def _assign_finish_positions(grp: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """グループ（同一 race_key）内で finish_position を 1〜N で重複なく割り当てる。

    人気順（popularity_rank）に近い順位になりやすいよう、軽いノイズを乗せる。
    """
    n = len(grp)
    grp = grp.copy()

    if "popularity_rank" in grp.columns and grp["popularity_rank"].notna().any():
        base = grp["popularity_rank"].fillna(n).astype(float).to_numpy()
        score = base + rng.normal(0, 2.5, n)
    else:
        score = rng.uniform(0, 10, n)

    # score が小さい馬ほど好走 → finish_position が 1 から
    order = np.argsort(score)
    finish = np.empty(n, dtype=int)
    for rank, idx in enumerate(order, start=1):
        finish[idx] = rank
    grp["finish_position"] = finish
    return grp


def main() -> int:
    p = argparse.ArgumentParser(description="疑似学習データ生成")
    p.add_argument("--src", required=True, help="ベースとなる features.parquet")
    p.add_argument("--out-base", default="C:/keiba-ai/runs", help="出力ベースディレクトリ")
    p.add_argument("--years", nargs="+", type=int,
                   default=[2018, 2019, 2020, 2021, 2022, 2023, 2024],
                   help="生成する年のリスト")
    p.add_argument("--weeks-per-year", type=int, default=12,
                   help="年あたりの週数（生成データ量の倍率）")
    args = p.parse_args()

    src_path = Path(args.src)
    if not src_path.exists():
        print(f"[ERROR] src 不在: {src_path}")
        return 1

    src = pd.read_parquet(src_path)
    print(f"src: {src_path}")
    print(f"  rows: {len(src)}, cols: {len(src.columns)}")
    print()

    out_base = Path(args.out_base)
    out_base.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(20260524)

    total_files = 0
    total_rows = 0

    for year in args.years:
        for week in range(1, args.weeks_per_year + 1):
            df = src.copy()

            # 月日を 0101 + week*7 日 で生成（うるう年は無視、超過は次月へ）
            day_offset = (week - 1) * 7 + 1  # 1〜85 程度
            month = (day_offset - 1) // 28 + 1
            day = (day_offset - 1) % 28 + 1
            mmdd = f"{month:02d}{day:02d}"

            # race_key 先頭 8 桁書き換え（残り 8 桁はそのまま）
            df["race_key"] = f"{year}{mmdd}" + df["race_key"].str[8:]
            df["entry_key"] = (
                df["race_key"]
                + df["horse_number"].astype(int).astype(str).str.zfill(2)
            )

            # finish_position 付与
            # NOTE: pandas 2.2+ では groupby.apply がグループキー列を戻り値から落とす
            # 仕様変更があり、include_groups=False が将来デフォルトになる予定。
            # 安全のため明示的な for ループで race_key 列を確実に保持する。
            grouped = []
            for _, g in df.groupby("race_key", sort=False):
                grouped.append(_assign_finish_positions(g, rng))
            df = pd.concat(grouped, ignore_index=True)

            run_dir = out_base / f"dummy_{year}_{week:02d}"
            run_dir.mkdir(parents=True, exist_ok=True)
            df.to_parquet(run_dir / "features.parquet", index=False)

            total_files += 1
            total_rows += len(df)

        print(f"  {year}: {args.weeks_per_year} 週生成完了")

    print()
    print(f"=== 完了 ===")
    print(f"  ファイル数: {total_files}")
    print(f"  総行数:     {total_rows}")
    print(f"  出力先:     {out_base}/dummy_*")
    print()
    print("次のステップ:")
    print(f"  python training/train_models.py \\")
    print(f"    --data-dir {out_base.as_posix()} \\")
    print(f"    --output-dir C:/keiba-ai/inference/models")

    return 0


if __name__ == "__main__":
    sys.exit(main())
