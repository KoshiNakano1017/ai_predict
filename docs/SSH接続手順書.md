# SSH 接続手順書 (Phase 1-C: 遠隔操作環境)

**根拠資料:** `17_ハイブリッド構成構築手順書.md` §6 Phase 1-C  
**標準接続方式:** Tailscale + SSH (OpenSSH)  
**作成日:** 2026-04-27

---

## 1. 概要

```
中野晃志のPC ──[Tailscale VPN]──► Dさんの Windows PC
                                       └─ OpenSSH Server
                                       └─ CrossFactor / keiba-ai
```

Tailscale がルーター NAT を透過するため、ポート開放不要。  
通信は WireGuard ベースで暗号化済み。

---

## 2. Tailscale インストール (両 PC 共通)

1. https://tailscale.com/download から Windows 用インストーラをダウンロード
2. インストーラを実行し、画面に従って完了
3. Google / Microsoft アカウントでサインイン
4. 同じアカウントで両 PC にログインすることで同一ネットワークに参加できる

**確認:**

```powershell
# Tailscale IP を確認 (100.x.x.x 形式)
tailscale ip -4
```

---

## 3. OpenSSH Server の有効化 (Dさんの PC)

```powershell
# 管理者権限の PowerShell で実行

# OpenSSH Server をインストール
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0

# サービスを起動
Start-Service sshd

# 自動起動に設定
Set-Service -Name sshd -StartupType 'Automatic'

# ファイアウォールルールを確認 (自動で作成されているはず)
Get-NetFirewallRule -Name "OpenSSH*"
```

---

## 4. SSH 接続テスト (中野晃志の PC から)

```powershell
# Dさんの Tailscale IP を使って接続 (ユーザー名は Dさんの Windows アカウント名)
ssh DさんのWindowsユーザー名@100.x.x.x

# 接続後に確認
python --version
cd C:\keiba-ai
python batch\run_pipeline.py --mode daily_evening --target-date 2026-04-01 --dry-run
```

---

## 5. SSH 公開鍵認証の設定 (推奨)

毎回パスワード入力を省略するため、公開鍵認証を設定する。

```powershell
# 中野晃志のPC で鍵ペアを生成 (既存の場合はスキップ)
ssh-keygen -t ed25519 -C "keiba-ai-ops"

# 公開鍵を Dさんの PC にコピー
# Windows では以下のコマンドを使う
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh DさんのWindowsユーザー名@100.x.x.x "powershell -command `"Add-Content -Force -Path $env:USERPROFILE\.ssh\authorized_keys -Value '$(Get-Content -Raw -)'`""
```

---

## 6. バッチ実行の遠隔操作コマンド

```powershell
# 今日分のバッチを実行
ssh DさんのWindowsユーザー名@100.x.x.x "C:\keiba-ai\.venv\Scripts\python.exe C:\keiba-ai\batch\run_pipeline.py --mode daily_evening"

# 特定日のバックフィル (SSH 内で実行)
ssh DさんのWindowsユーザー名@100.x.x.x "C:\keiba-ai\.venv\Scripts\python.exe C:\keiba-ai\batch\run_pipeline.py --mode backfill --from 2026-04-01 --to 2026-04-30"

# ファイル転送 (ログを手元に取得)
scp DさんのWindowsユーザー名@100.x.x.x:C:/keiba-ai/logs/batch_20260427_*.log ./logs/

# モデルファイルを配置
scp ./inference/models/lgbm_win_v1.pkl DさんのWindowsユーザー名@100.x.x.x:C:/keiba-ai/inference/models/
```

---

## 7. RDP 接続 (GUI が必要な場合のみ)

Tailscale 経由で RDP を使うことで、ポート開放なしに GUI 操作ができる。

```powershell
# Dさんの PC で RDP を有効化 (管理者 PowerShell)
Set-ItemProperty -Path "HKLM:\System\CurrentControlSet\Control\Terminal Server" -Name "fDenyTSConnections" -Value 0
Enable-NetFirewallRule -DisplayGroup "Remote Desktop"

# 中野晃志のPC から接続
mstsc /v:100.x.x.x   # Dさんの Tailscale IP
```

---

## 8. 接続確認チェックリスト

| # | 確認項目 | 合格基準 |
|---|---------|---------|
| 1 | Tailscale IP の確認 | 両 PC が `100.x.x.x` 形式の IP を持つ |
| 2 | SSH 接続 | `ssh user@100.x.x.x` でログインできる |
| 3 | Python 確認 | `python --version` が返る |
| 4 | バッチ dry-run | `run_pipeline.py --dry-run` がエラーなく完了する |
| 5 | ファイル転送 | `scp` で .log ファイルを取得できる |
| 6 | 再接続 | 一度切断後に再接続できる |

---

## 9. トラブルシューティング

| 症状 | 原因 | 対処 |
|------|------|------|
| SSH 接続タイムアウト | OpenSSH Server が停止 | `Start-Service sshd` を実行 |
| Tailscale IP に到達できない | Tailscale が未起動 | Tailscale アプリを起動 |
| 認証失敗 | ユーザー名の誤り | Windows アカウント名を確認 |
| `python` が見つからない | PATH 未設定 | フルパス `C:\keiba-ai\.venv\Scripts\python.exe` を使用 |
