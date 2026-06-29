# ai_predict

AI を用いた **競艇（ボートレース）** 勝敗予測パッケージです。  
レースデータの収集・特徴量生成から **LightGBM** による確率予測、**SHAP** による予測根拠の説明、Web フロントでの閲覧・課金までを一貫して扱います。

> **現状:** Web フロントは競艇向け UI・モックデータでデモ可能です。AI バッチパイプラインは LightGBM / SHAP 基盤を実装済みで、競艇データソースへの接続を進めています。

---

## 主な機能

| 領域 | 内容 |
|------|------|
| **予測** | 各艇の勝率・2連対率・3連対率・期待値の算出 |
| **説明** | SHAP 値から「AIの一言」（予測根拠テキスト）を自動生成 |
| **Web** | レース一覧・詳細・プラン別ロック表示（無料 / プロ） |
| **認証・課金** | Supabase Auth + Stripe Billing |
| **バッチ** | 抽出 → 変換 → 学習 / 推論 → Supabase 公開 |

---

## 技術スタック

### Web フロントエンド（`source/`）

| 項目 | 技術 |
|------|------|
| フレームワーク | Next.js 15 (App Router) |
| 言語 | TypeScript (strict) |
| スタイル | Tailwind CSS 3 |
| 認証 | Supabase Auth (`@supabase/ssr`) |
| 決済 | Stripe Billing |
| ホスティング | Vercel |

### AI / バッチ（ルート直下）

| 項目 | 技術 |
|------|------|
| 言語 | Python 3.10+ |
| **機械学習** | **LightGBM**（勾配ブースティング） |
| **説明可能性** | **SHAP**（SHapley Additive exPlanations） |
| データ処理 | pandas, NumPy, scikit-learn |
| DB（AI基盤） | PostgreSQL（VM 上） |
| DB（Web表示） | Supabase (PostgreSQL) |
| スケジューラ | systemd timer / cron |

---

## LightGBM について

本プロジェクトの予測エンジンは [LightGBM](https://lightgbm.readthedocs.io/)（Microsoft 製の勾配ブースティングライブラリ）を採用しています。

### 採用理由

- **学習・推論が高速** — 日次バッチでの全レース推論に適する
- **表形式データに強い** — 選手成績・モーター指数・コース・オッズなどの特徴量をそのまま扱える
- **欠損値・カテゴリ変数を扱いやすい** — 競艇データの多様な属性に対応しやすい
- **確率較正と組み合わせ可能** — 勝率をレース内で正規化して期待値計算に利用

### モデル構成

| モデル | 出力ファイル | 目的 |
|--------|-------------|------|
| 勝率モデル | `lgbm_win_v1.pkl` | 1着確率（`is_win`） |
| 2連対モデル | `lgbm_top2_v1.pkl` | 2着以内確率（`is_top2`） |
| 3連対モデル | `lgbm_top3_v1.pkl` | 3着以内確率（`is_top3`） |

### 関連スクリプト

```bash
# 学習（features.parquet から時系列分割で学習）
python training/train_models.py --data-dir <runs> --output-dir <models>

# 推論（学習済みモデルで勝率・期待値を算出）
python inference/run_inference.py
```

詳細は `docs/15_AIモデル入出力・テスト仕様書.md` を参照してください。

---

## SHAP について

予測の「なぜ」をユーザーに伝えるため、[SHAP](https://shap.readthedocs.io/)（SHapley Additive exPlanations）を用いて特徴量の寄与度を可視化・文章化します。

### 役割

| 用途 | 説明 |
|------|------|
| **AIの一言** | SHAP 値の上位特徴量を定型テンプレートに当てはめ、自然言語の予測根拠を生成 |
| **重要度検証** | 学習後の特徴量重要度を `TreeExplainer` で確認し、設計した特徴量が妥当か検証 |
| **納品・分析** | ウォーターフォール図・サマリープロットをレポートとして提供 |

### 生成イメージ

```
好材料: モーター2連対率(72.1%)、当地勝率(38.5%)、展示タイム(6.78秒)
懸念: スタート展示順位(5位)、進入コース変更
```

ブラックボックス化を避げ、プロプラン利用者が「なぜこの艇か」を理解できることを設計方針としています（`docs/01_AI正解定義.md` 参照）。

---

## リポジトリ構成

```
ai_predict/
├── source/          # Next.js Web フロントエンド
├── batch/           # 日次パイプライン実行
├── extract/         # データ抽出
├── transform/       # 特徴量変換・正規化
├── training/        # LightGBM 学習
├── inference/       # LightGBM 推論
├── load/            # Supabase / PostgreSQL への投入
├── db/              # AI 用 DB マイグレーション
├── scripts/         # 運用・検証スクリプト
├── scheduler/       # systemd / cron 定義
├── tests/           # pytest
└── docs/            # 仕様書・設計書（SSOT）
```

---

## クイックスタート

### 競艇デモ（UI のみ・モックデータ）

```bash
cd source
cp .env.example .env.local
# .env.local に以下を設定:
#   NEXT_PUBLIC_SPORT=kyotei
#   NEXT_PUBLIC_USE_REAL_DATA=false
npm install
npm run dev
```

→ http://localhost:3000 で競艇モック（平和島・住之江・福岡など）が表示されます。

### AI バッチ（Python）

```bash
pip install -r requirements.txt
cp .env.example .env
# config.yaml / .env を環境に合わせて編集
python batch/run_pipeline.py
```

---

## 環境変数（フロント）

| 変数名 | 用途 | デモ時の推奨値 |
|--------|------|---------------|
| `NEXT_PUBLIC_SPORT` | 競技種別 | `kyotei` |
| `NEXT_PUBLIC_USE_REAL_DATA` | 実データ / モック切替 | `false` |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase URL | プロジェクトの値 |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon key | プロジェクトの値 |

フロントの詳細は [`source/README.md`](source/README.md) を参照してください。

---

## ドキュメント

| ドキュメント | 内容 |
|-------------|------|
| `docs/10_要件定義書.md` | 全体要件・技術選定 |
| `docs/01_AI正解定義.md` | KPI・AI 出力仕様・SHAP 説明文 |
| `docs/11_特徴量設計.md` | 特徴量一覧・SHAP 検証手順 |
| `docs/15_AIモデル入出力・テスト仕様書.md` | LightGBM モデル I/O 仕様 |

---

## 今後の展望

- 競艇データソース（公式・スクレイピング等）への接続
- 競艇固有特徴量（モーター・ボート・進入コース・当地成績）の設計・学習
- スポーツ全般に適用可能な予測モデリングの抽象化
- マルチスポーツ対応のデータ収集基盤の構築

---

## ライセンス

（未定）
