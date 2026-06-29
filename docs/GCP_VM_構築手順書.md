# GCP VM 構築・運用手順書

> 対象: CrossFactor AI 基盤の GCP VM への移行  
> 目的: Web側は Supabase 据え置き、AI処理のみ GCP VM + PostgreSQL へ移す  
> 更新: 2026-05-10

---

## 目次

1. [アーキテクチャ概要](#1-アーキテクチャ概要)
2. [GCP VM 作成手順](#2-gcp-vm-作成手順)
3. [VM 初期セットアップ](#3-vm-初期セットアップ)
4. [PostgreSQL 構築確認](#4-postgresql-構築確認)
5. [環境変数設定](#5-環境変数設定)
6. [動作確認テスト](#6-動作確認テスト)
7. [スケジューラ確認](#7-スケジューラ確認)
8. [日次運用手順](#8-日次運用手順)
9. [障害復旧手順](#9-障害復旧手順)
10. [バックアップ確認](#10-バックアップ確認)

---

## 1. アーキテクチャ概要

```
CrossFactor SQLite (Windows PC)
        │
        │ SSH / SCP
        ▼
┌─────────────────────────────────────────┐
│  GCP VM (e2-micro, us-central1)         │
│  Ubuntu 22.04 / pd-standard 30GB        │
│                                         │
│  run_pipeline_vm.py                     │
│    │                                    │
│    ├─ extract (SQLite読取)              │
│    ├─ transform (特徴量生成)            │
│    ├─ VM Postgres (keiba_ai)            │
│    │    ├─ raw_races                    │
│    │    ├─ raw_entries                  │
│    │    ├─ features                     │
│    │    ├─ predictions_staging          │
│    │    └─ job_runs                     │
│    │                                    │
│    └─ LightGBM 推論                    │
│                                         │
│  バックアップ: GCS                      │
└─────────────────────────────────────────┘
        │
        │ HTTPS (Supabase REST API)
        │ 送信するのは最終成果物のみ
        ▼
┌────────────────────────────────────┐
│  Supabase                          │
│    races  (基本情報)               │
│    entries (基本情報 + AI予測列)   │
│    users / Auth / RLS  ← 触らない  │
└────────────────────────────────────┘
        ▲
        │
   Vercel (Next.js フロント)
```

**Supabase へ送信するカラム（予測列のみ）:**

| カラム | 説明 |
|--------|------|
| `entry_key` | Upsert キー |
| `win_rate` | 勝率 (%) |
| `place_rate` | 連対率 (%) |
| `show_rate` | 複勝率 (%) |
| `expected_value_win` | 単勝期待値 |
| `expected_value_place` | 複勝期待値 |
| `star_rating` | ★/▲/⚠/◆ |
| `ai_comment` | AIコメント |
| `inference_at` | 推論実行時刻 |
| `model_version` | モデルバージョン |

**絶対に送らないテーブル:** `users`, `auth`, `roles`, `subscriptions`, `plans`

---

## 2. GCP VM 作成手順

### 2-1. gcloud CLI でVM作成

```bash
# プロジェクト設定
gcloud config set project YOUR_GCP_PROJECT_ID

# VM 作成（Always Free 対象: e2-micro, us-central1, pd-standard 30GB以内）
gcloud compute instances create keiba-ai-vm \
    --zone=us-central1-a \
    --machine-type=e2-micro \
    --image-family=ubuntu-2204-lts \
    --image-project=ubuntu-os-cloud \
    --boot-disk-size=30GB \
    --boot-disk-type=pd-standard \
    --tags=ai-vm \
    --scopes=cloud-platform
```

### 2-2. Firewall ルール（SSH のみ）

```bash
# SSH のみ開放（デフォルトで有効なはず）
gcloud compute firewall-rules create allow-ssh-ai-vm \
    --direction=INGRESS \
    --priority=1000 \
    --network=default \
    --action=ALLOW \
    --rules=tcp:22 \
    --source-ranges=YOUR_IP_ADDRESS/32 \
    --target-tags=ai-vm
```

> **注意:** `YOUR_IP_ADDRESS` は自分の固定IPに限定すること。`0.0.0.0/0` は使わない。

### 2-3. SSH 接続確認

```bash
gcloud compute ssh keiba-ai-vm --zone=us-central1-a
```

---

## 3. VM 初期セットアップ

### 3-1. セットアップスクリプト実行

```bash
# VM 上で実行
export REPO_URL=https://github.com/YOUR_ORG/YOUR_REPO.git
export AI_DB_PASSWORD="STRONG_PASSWORD_HERE"
export GCS_BUCKET="your-gcs-bucket-name"

sudo bash /opt/keiba-ai/scripts/setup_vm.sh
```

スクリプトが行うこと:
- Python 3.11 + venv + requirements.txt インストール
- PostgreSQL 14 インストール・起動
- `keiba_ai` DB + `ai_runner` ユーザー作成
- DDL マイグレーション適用 (`001_create_ai_tables.sql`)
- systemd タイマー登録

### 3-2. 手動でのDBマイグレーション適用（再実行時）

```bash
export PGPASSWORD="your_password"
psql -h localhost -U ai_runner -d keiba_ai \
    -f /opt/keiba-ai/db/migrations/001_create_ai_tables.sql
```

---

## 4. PostgreSQL 構築確認

```bash
# DB 接続確認
psql -h localhost -U ai_runner -d keiba_ai -c "\dt"

# テーブル一覧確認（以下5テーブルが存在すること）
# raw_races / raw_entries / features / predictions_staging / job_runs

# サービス状態確認
systemctl status postgresql
```

---

## 5. 環境変数設定

`/opt/keiba-ai/.env` を編集する（`.env.example` を参照）:

```bash
sudo nano /opt/keiba-ai/.env
```

**必須設定項目:**

```bash
# Supabase
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciO...

# VM Postgres
AI_DB_HOST=localhost
AI_DB_PORT=5432
AI_DB_NAME=keiba_ai
AI_DB_USER=ai_runner
AI_DB_PASSWORD=STRONG_PASSWORD

# GCS
GCP_PROJECT_ID=your-project-id
GCS_BUCKET=your-bucket-name

# モデルバージョン（必須）
MODEL_VERSION=v1.0.0

# メール通知
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@gmail.com
SMTP_PASSWORD=app_password
MAIL_FROM=your@gmail.com
MAIL_TO=alert@example.com
```

---

## 6. 動作確認テスト

### 6-1. dry-run（DB/Supabase に書き込まない）

```bash
cd /opt/keiba-ai
source .venv/bin/activate

python batch/run_pipeline_vm.py \
    --mode daily_evening \
    --target-date $(date +%Y-%m-%d) \
    --dry-run
```

**確認ポイント:**
- `[pipeline_vm] 対象レースなし` または `差分なし` が出なければ正常進行
- エラーなく `[pipeline_vm] 正常完了` が出ること

### 6-2. 各ステップの個別確認

```bash
# SQLite → VM DB 取り込み確認
python -c "
from db.postgres_client import init_pool, get_conn
import psycopg2.extras
init_pool()
with get_conn() as conn:
    with conn.cursor() as cur:
        cur.execute('SELECT COUNT(*) FROM raw_races')
        print('raw_races:', cur.fetchone()[0])
        cur.execute('SELECT COUNT(*) FROM raw_entries')
        print('raw_entries:', cur.fetchone()[0])
        cur.execute('SELECT COUNT(*) FROM predictions_staging')
        print('predictions_staging:', cur.fetchone()[0])
"

# 特徴量欠損率チェック
python -c "
from db.postgres_client import init_pool, get_conn
import pandas as pd
import psycopg2.extras
init_pool()
with get_conn() as conn:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute('SELECT COUNT(*) as total, COUNT(win_prob) as win_cnt FROM predictions_staging')
        r = cur.fetchone()
        total = r['total']
        win = r['win_cnt']
        print(f'predictions: {win}/{total} ({win/total*100:.1f}%)')
"

# Supabase upsert 確認（未反映件数）
python -c "
from load.supabase_publisher import fetch_unpublished
df = fetch_unpublished()
print(f'未反映件数: {len(df)}')
"
```

### 6-3. 実際に実行（本番）

```bash
python batch/run_pipeline_vm.py \
    --mode daily_evening \
    --target-date 2026-05-10
```

**検収チェックリスト:**

- [ ] SQLite → VM DB 取り込み成功（raw_races / raw_entries に行があること）
- [ ] features テーブルに特徴量が保存されていること
- [ ] predictions_staging に推論結果があること（win_prob 欠損率 < 5%）
- [ ] Supabase entries に予測列が反映されていること（Vercel 画面で確認）
- [ ] job_runs に `status=success` のレコードがあること
- [ ] 再実行しても件数が重複しないこと（冪等確認）

---

## 7. スケジューラ確認

### systemd timer 確認

```bash
# タイマー一覧と次回実行時刻
systemctl list-timers --all | grep -E "(daily-evening|race-day|pre-race|pg-backup)"

# 手動実行テスト
systemctl start daily-evening.service
journalctl -u daily-evening.service -n 50
```

### cron 使用の場合

```bash
# crontab 適用
crontab /opt/keiba-ai/scheduler/crontab.example

# 確認
crontab -l
```

---

## 8. 日次運用手順

### 毎日確認すること

```bash
# 最新の job_runs を確認
psql -h localhost -U ai_runner -d keiba_ai -c "
SELECT id, job_name, target_date, status, 
       rows_predictions, rows_published,
       started_at, finished_at
FROM job_runs
ORDER BY started_at DESC
LIMIT 10;
"

# 失敗ジョブの確認
psql -h localhost -U ai_runner -d keiba_ai -c "
SELECT id, job_name, target_date, error_message
FROM job_runs
WHERE status = 'failed'
AND started_at > now() - interval '7 days'
ORDER BY started_at DESC;
"

# ログ確認
tail -n 50 /opt/keiba-ai/logs/daily_evening.log
```

### 手動再実行（失敗時）

```bash
cd /opt/keiba-ai
source .venv/bin/activate

# dry-run で確認してから実行
python batch/run_pipeline_vm.py \
    --mode daily_evening \
    --target-date 2026-05-10 \
    --dry-run

# 問題なければ本実行
python batch/run_pipeline_vm.py \
    --mode daily_evening \
    --target-date 2026-05-10
```

### Supabase 未反映データを再投入する

```bash
python -c "
import os
os.chdir('/opt/keiba-ai')
from dotenv import load_dotenv
load_dotenv()
from db.postgres_client import init_pool
from load import supabase_client as sb
from load.supabase_publisher import fetch_unpublished, publish_predictions, mark_published
from datetime import datetime, timezone

init_pool()
cfg_url = os.getenv('SUPABASE_URL')
cfg_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
client = sb.get_client(cfg_url, cfg_key)

df = fetch_unpublished()
print(f'未反映: {len(df)} 件')
if len(df) > 0:
    model_version = os.getenv('MODEL_VERSION', 'v1.0.0')
    published = publish_predictions(client, df, model_version)
    mark_published(df['entry_key'].tolist(), datetime.now(timezone.utc).isoformat())
    print(f'反映完了: {published} 件')
"
```

---

## 9. 障害復旧手順

### VM が落ちていた場合

```bash
# VM 起動
gcloud compute instances start keiba-ai-vm --zone=us-central1-a

# SSH 接続後
systemctl start postgresql
systemctl start daily-evening.timer race-day-morning.timer pre-race.timer pg-backup.timer

# 欠損日を backfill
cd /opt/keiba-ai && source .venv/bin/activate
python batch/run_pipeline_vm.py \
    --mode backfill \
    --from 2026-05-08 \
    --to 2026-05-10
```

### PostgreSQL が起動しない場合

```bash
journalctl -u postgresql -n 100
systemctl restart postgresql

# データ整合性確認
psql -h localhost -U ai_runner -d keiba_ai -c "SELECT COUNT(*) FROM raw_races"
```

### GCS からのリストア

```bash
# モデルファイルのリストア
gsutil -m cp "gs://YOUR_BUCKET/backup/models/*.pkl" /opt/keiba-ai/inference/models/

# DB リストア（最終手段）
gsutil cp "gs://YOUR_BUCKET/backup/postgres/keiba_ai_YYYYMMDD_HHMMSS.sql.gz" /tmp/
gunzip /tmp/keiba_ai_*.sql.gz
psql -h localhost -U ai_runner -d keiba_ai -f /tmp/keiba_ai_*.sql
```

### Supabase 側のデータが壊れた場合

Supabase への送信は `entry_key` キーの Upsert なので、  
`run_pipeline_vm.py` を再実行すれば冪等に上書きされる。

```bash
# 対象日を指定して再実行（重複しない）
python batch/run_pipeline_vm.py --mode pre_race --target-date 2026-05-10
```

---

## 10. バックアップ確認

```bash
# 手動バックアップ実行
bash /opt/keiba-ai/scripts/backup_postgres.sh

# GCS に保存されているか確認
gsutil ls "gs://YOUR_BUCKET/backup/postgres/"
gsutil ls "gs://YOUR_BUCKET/backup/models/"

# バックアップサイズ確認
gsutil du -sh "gs://YOUR_BUCKET/backup/"
```

---

## 変更ファイル一覧（今回の移行で追加・変更したファイル）

| ファイル | 種別 | 説明 |
|----------|------|------|
| `db/__init__.py` | 新規 | パッケージ初期化 |
| `db/postgres_client.py` | 新規 | psycopg2 接続プール |
| `db/migrations/001_create_ai_tables.sql` | 新規 | VM Postgres DDL（冪等） |
| `load/vm_loader.py` | 新規 | SQLite → VM Postgres 投入 |
| `load/supabase_publisher.py` | 新規 | Supabase 最終成果反映（予測列のみ） |
| `batch/run_pipeline_vm.py` | 新規 | 2段化ETL メインパイプライン |
| `batch/config.py` | 変更 | VmDbConfig / MODEL_VERSION 追加 |
| `scripts/setup_vm.sh` | 新規 | Ubuntu VM セットアップ |
| `scripts/backup_postgres.sh` | 新規 | pg_dump → GCS |
| `scheduler/crontab.example` | 新規 | cron 設定 |
| `scheduler/daily-evening.{service,timer}` | 新規 | systemd タイマー |
| `scheduler/race-day-morning.{service,timer}` | 新規 | systemd タイマー |
| `scheduler/pre-race.{service,timer}` | 新規 | systemd タイマー |
| `scheduler/pg-backup.{service,timer}` | 新規 | systemd タイマー |
| `.env.example` | 変更 | AI_DB_* / GCS / MODEL_VERSION 追加 |
| `requirements.txt` | 変更 | psycopg2-binary 追加 |
| `docs/GCP_VM_構築手順書.md` | 新規 | 本書 |

## 追加した環境変数一覧

| 変数名 | 説明 | 必須 |
|--------|------|------|
| `AI_DB_HOST` | VM Postgres ホスト | ✓ |
| `AI_DB_PORT` | VM Postgres ポート | ✓ |
| `AI_DB_NAME` | DB 名（keiba_ai） | ✓ |
| `AI_DB_USER` | DB ユーザー（ai_runner） | ✓ |
| `AI_DB_PASSWORD` | DB パスワード | ✓ |
| `AI_DB_DSN` | 直接 DSN 文字列（省略可） | |
| `GCP_PROJECT_ID` | GCP プロジェクト ID | ✓ |
| `GCS_BUCKET` | GCS バケット名 | ✓ |
| `MODEL_VERSION` | モデルバージョン文字列 | ✓ |
| `BACKUP_RETENTION_DAYS` | ローカルバックアップ保持日数 | |
| `GCS_BACKUP_RETENTION_DAYS` | GCS バックアップ保持日数 | |

## 次に人間が行う手順（コンソール操作）

1. **GCP コンソール**: VM 作成（`gcloud` コマンドで代替可）
2. **GCP コンソール**: GCS バケット作成  
   `gsutil mb -l us-central1 gs://YOUR_BUCKET/`
3. **GCP コンソール**: Workload Identity または サービスアカウントキー発行 → VM に配置  
   `gcloud iam service-accounts create keiba-ai-sa`
4. **Supabase ダッシュボード**: `entries` テーブルに `inference_at` / `model_version` 列が存在するか確認（なければ Migration 追加）
5. **SSH**: `.env` に実際の値を設定
6. **SSH**: モデルファイル (`.pkl`) を `inference/models/` に配置
7. **Vercel 画面**: 推論結果が表示されることを確認
