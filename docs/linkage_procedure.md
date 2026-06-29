# KeibaAI 期待値修正・連携手順

## 1. 期待値（EV）計算ロジックの修正
`keiba/scripts/import_race_csv.py` および `keiba/inference/run_inference.py` において、人気薄（穴馬）の期待値が正しく算出されるよう、以下の通り修正済み。

- **修正点**: 7番人気以下の「AI補正倍率」を 1.40 → **1.45〜1.60** に引き上げ。
- **効果**: `EV >= 1.05` の穴馬（◆）が適切に検出され、Proプランのセクションが埋まるようになる。

## 2. AI推論結果との連携（Linkage）

手入力 CSV ではなく、実際の AI モデルの推論結果を Supabase に反映する手順。

### ステップ 1: 特徴量抽出と推論
```bash
# VMまたはローカル環境で実行
python keiba/inference/run_inference.py
```
※ `df_pred` に `win_rate`, `expected_value_win` 等が格納される。

### ステップ 2: Supabase への反映
`keiba/load/upsert_entries.py` の `upsert_predictions` 関数を使用して、予測値のみを同期する。

**連携コマンド案**:
```python
from load.supabase_client import create_client
from load.upsert_entries import upsert_predictions

client = create_client()
# run_inference で得られた df_pred を投入
upsert_predictions(client, df_pred)
```

## 3. フロントエンドとの連携確認
1. `localhost:3000` を起動。
2. 期待値が 1.05 以上の馬に `◆` マークがついていることを確認。
3. プロプランでログインし、期待値列がモザイクなしで表示されることを確認。

---
## 【ファクト判事】
- 期待値はあくまで「統計的な妙味」であり、的中を保証するものではありません。
- オッズは直前まで変動するため、確定オッズではなく「想定オッズ」での計算である点に注意。
