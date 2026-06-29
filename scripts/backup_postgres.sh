#!/usr/bin/env bash
# =============================================================
# VM 内 PostgreSQL の日次バックアップ → GCS
# cron / systemd から呼ぶ想定
#
# 使い方:
#   bash scripts/backup_postgres.sh
#   環境変数 GCS_BUCKET, AI_DB_* が設定済みであること
# =============================================================
set -euo pipefail

# ── 設定（環境変数で上書き可能）────────────────────────────
DB_NAME="${AI_DB_NAME:-keiba_ai}"
DB_USER="${AI_DB_USER:-ai_runner}"
DB_HOST="${AI_DB_HOST:-localhost}"
DB_PORT="${AI_DB_PORT:-5432}"
GCS_BUCKET="${GCS_BUCKET:?GCS_BUCKET 環境変数が未設定です}"
BACKUP_DIR="${BACKUP_DIR:-/opt/keiba-ai/backup}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
PROJECT_DIR="${PROJECT_DIR:-/opt/keiba-ai}"
MODEL_DIR="${PROJECT_DIR}/inference/models"
LOG_FILE="${PROJECT_DIR}/logs/backup_$(date +%Y%m%d_%H%M%S).log"

log() { echo "[backup] $(date '+%F %T') $*" | tee -a "${LOG_FILE}"; }
die() { log "ERROR: $*"; exit 1; }

mkdir -p "${BACKUP_DIR}" "$(dirname "${LOG_FILE}")"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DUMP_FILE="${BACKUP_DIR}/${DB_NAME}_${TIMESTAMP}.sql.gz"

# ──────────────────────────────────────
# 1. pg_dump → gzip → GCS
# ──────────────────────────────────────
log "pg_dump 開始: ${DB_NAME}"
export PGPASSWORD="${AI_DB_PASSWORD:-}"
pg_dump \
    -h "${DB_HOST}" \
    -p "${DB_PORT}" \
    -U "${DB_USER}" \
    -d "${DB_NAME}" \
    --no-password \
    | gzip > "${DUMP_FILE}" || die "pg_dump 失敗"
unset PGPASSWORD

log "pg_dump 完了: $(du -sh "${DUMP_FILE}" | cut -f1) -> ${DUMP_FILE}"

GCS_DB_TARGET="gs://${GCS_BUCKET}/backup/postgres/${DB_NAME}_${TIMESTAMP}.sql.gz"
gsutil cp "${DUMP_FILE}" "${GCS_DB_TARGET}" || die "GCS DB バックアップ転送失敗"
log "GCS 転送完了: ${GCS_DB_TARGET}"

# ──────────────────────────────────────
# 2. モデルファイル → GCS
# ──────────────────────────────────────
if [ -d "${MODEL_DIR}" ] && ls "${MODEL_DIR}"/*.pkl &>/dev/null 2>&1; then
    log "モデルファイルを GCS へ同期"
    gsutil -m rsync -r "${MODEL_DIR}" "gs://${GCS_BUCKET}/backup/models/" \
        || log "WARNING: モデルバックアップ失敗（続行）"
    log "モデルバックアップ完了"
else
    log "モデルファイルなし（スキップ）: ${MODEL_DIR}"
fi

# ──────────────────────────────────────
# 3. ローカル古いバックアップを削除（世代管理）
# ──────────────────────────────────────
log "ローカル ${RETENTION_DAYS} 日超のバックアップを削除"
find "${BACKUP_DIR}" -name "*.sql.gz" -mtime "+${RETENTION_DAYS}" -delete
log "古いバックアップ削除完了"

# ──────────────────────────────────────
# 4. GCS 古いバックアップ削除（30日超）
# ──────────────────────────────────────
GCS_RETENTION_DAYS="${GCS_BACKUP_RETENTION_DAYS:-30}"
CUTOFF=$(date -d "${GCS_RETENTION_DAYS} days ago" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null \
         || date -v-${GCS_RETENTION_DAYS}d +%Y-%m-%dT%H:%M:%SZ)  # macOS fallback

log "GCS ${GCS_RETENTION_DAYS} 日超のバックアップを削除 (cutoff: ${CUTOFF})"
gsutil ls -l "gs://${GCS_BUCKET}/backup/postgres/" 2>/dev/null \
    | grep "\.sql\.gz" \
    | awk -v cutoff="${CUTOFF}" '$2 < cutoff {print $3}' \
    | while read -r uri; do
        gsutil rm "${uri}" && log "GCS 削除: ${uri}"
    done || log "WARNING: GCS 世代削除失敗（続行）"

log "バックアップ全工程完了"
