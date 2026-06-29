#!/usr/bin/env bash
# =============================================================
# GCP VM (Ubuntu 22.04) AI実行基盤セットアップスクリプト
# 実行: sudo bash scripts/setup_vm.sh
# =============================================================
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/YOUR_ORG/YOUR_REPO.git}"
PROJECT_DIR="${PROJECT_DIR:-/opt/keiba-ai}"
VENV_DIR="${PROJECT_DIR}/.venv"
DB_NAME="${AI_DB_NAME:-keiba_ai}"
DB_USER="${AI_DB_USER:-ai_runner}"
DB_PASSWORD="${AI_DB_PASSWORD:-CHANGE_ME}"
PYTHON_VERSION="3.11"
GCS_BUCKET="${GCS_BUCKET:-}"

log() { echo "[setup] $*"; }

# ──────────────────────────────────────
# 1. システムパッケージ
# ──────────────────────────────────────
log "apt update & install"
apt-get update -y
apt-get install -y \
    software-properties-common curl git \
    postgresql postgresql-contrib libpq-dev \
    python${PYTHON_VERSION} python${PYTHON_VERSION}-venv python${PYTHON_VERSION}-dev \
    python3-pip \
    apt-transport-https ca-certificates gnupg

# ──────────────────────────────────────
# 2. gcloud CLI
# ──────────────────────────────────────
if ! command -v gcloud &>/dev/null; then
    log "gcloud CLI インストール"
    curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg \
        | gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg
    echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] \
        https://packages.cloud.google.com/apt cloud-sdk main" \
        > /etc/apt/sources.list.d/google-cloud-sdk.list
    apt-get update -y
    apt-get install -y google-cloud-cli
fi

# ──────────────────────────────────────
# 3. プロジェクト配置
# ──────────────────────────────────────
if [ ! -d "${PROJECT_DIR}/.git" ]; then
    log "git clone -> ${PROJECT_DIR}"
    git clone "${REPO_URL}" "${PROJECT_DIR}"
else
    log "git pull (既存リポジトリ更新)"
    git -C "${PROJECT_DIR}" pull --ff-only
fi

# ──────────────────────────────────────
# 4. Python 仮想環境 + 依存パッケージ
# ──────────────────────────────────────
log "仮想環境作成: ${VENV_DIR}"
python${PYTHON_VERSION} -m venv "${VENV_DIR}"
"${VENV_DIR}/bin/pip" install --upgrade pip wheel
"${VENV_DIR}/bin/pip" install -r "${PROJECT_DIR}/requirements.txt"

# ──────────────────────────────────────
# 5. VM 内 PostgreSQL 構築
# ──────────────────────────────────────
log "PostgreSQL 起動・有効化"
systemctl enable postgresql
systemctl start postgresql

# DB / ユーザー作成（冪等）
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" \
    | grep -q 1 || sudo -u postgres psql -c "
        CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';
    "

sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" \
    | grep -q 1 || sudo -u postgres psql -c "
        CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};
    "

sudo -u postgres psql -d "${DB_NAME}" -c "
    GRANT ALL PRIVILEGES ON SCHEMA public TO ${DB_USER};
"

# ──────────────────────────────────────
# 6. DDL マイグレーション適用
# ──────────────────────────────────────
log "DDL マイグレーション適用"
export PGPASSWORD="${DB_PASSWORD}"
psql -h localhost -U "${DB_USER}" -d "${DB_NAME}" \
    -f "${PROJECT_DIR}/db/migrations/001_create_ai_tables.sql"
unset PGPASSWORD

# ──────────────────────────────────────
# 7. .env ファイル配置
# ──────────────────────────────────────
if [ ! -f "${PROJECT_DIR}/.env" ]; then
    log ".env.example を .env にコピー（要編集）"
    cp "${PROJECT_DIR}/.env.example" "${PROJECT_DIR}/.env"
    log "!!! ${PROJECT_DIR}/.env を編集して実際の値を設定してください !!!"
fi

# ──────────────────────────────────────
# 8. ディレクトリ作成
# ──────────────────────────────────────
log "実行ディレクトリ作成"
mkdir -p "${PROJECT_DIR}/runs" \
         "${PROJECT_DIR}/logs" \
         "${PROJECT_DIR}/inference/models" \
         "${PROJECT_DIR}/backup"

# ──────────────────────────────────────
# 9. systemd サービス登録
# ──────────────────────────────────────
log "systemd サービスファイルをコピー"
cp "${PROJECT_DIR}/scheduler/"*.service /etc/systemd/system/ 2>/dev/null || true
cp "${PROJECT_DIR}/scheduler/"*.timer   /etc/systemd/system/ 2>/dev/null || true
systemctl daemon-reload

for TIMER in daily-evening race-day-morning pre-race pg-backup; do
    if systemctl list-unit-files "${TIMER}.timer" &>/dev/null; then
        systemctl enable "${TIMER}.timer"
        systemctl start  "${TIMER}.timer"
        log "タイマー有効化: ${TIMER}.timer"
    fi
done

# ──────────────────────────────────────
# 10. 完了メッセージ
# ──────────────────────────────────────
log "========================================================"
log "セットアップ完了！次のステップ:"
log "  1. ${PROJECT_DIR}/.env を編集して Supabase URL / GCS バケット等を設定"
log "  2. モデルファイルを ${PROJECT_DIR}/inference/models/ に配置"
log "  3. 動作確認:"
log "     ${VENV_DIR}/bin/python batch/run_pipeline_vm.py --mode daily_evening --target-date \$(date +%Y-%m-%d) --dry-run"
log "========================================================"
