# -*- coding: utf-8 -*-
import sys, io
import pandas as pd
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

runs = sorted(Path("C:/keiba-ai/runs").glob("*"), reverse=True)
# dummy_ ではない最新を取得
latest = next(d for d in runs if not d.name.startswith("dummy_"))
print(f"latest run: {latest}")
print()

# features
df_f = pd.read_parquet(latest / "features.parquet")
# predictions
df_p = pd.read_parquet(latest / "predictions.parquet")

print(f"=== predictions.parquet ===")
print(f"  rows: {len(df_p)}")
print(f"  cols: {list(df_p.columns)}")
print()

# Star rating の分布
print(f"=== star_rating 分布 ===")
print(df_p["star_rating"].value_counts(dropna=False).to_string())
print()

# サンプル: 1 レースの結果
sample_rk = df_p["race_key"].iloc[0]
sample = df_p[df_p["race_key"] == sample_rk].sort_values("win_rate", ascending=False)
sample = sample.merge(df_f[["entry_key", "horse_name", "jockey_name"]], on="entry_key", how="left")
print(f"=== サンプル（race_key={sample_rk}） ===")
cols = ["horse_number", "horse_name", "jockey_name",
        "win_odds", "popularity_rank",
        "win_rate", "place_rate", "show_rate",
        "expected_value_win", "expected_value_place",
        "star_rating"]
print(sample[cols].to_string(index=False))
