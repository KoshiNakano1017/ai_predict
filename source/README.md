# CrossFactor AI Web Frontend

CrossFactor AI 競馬予測Webサービスのフロントエンドです。

## 技術スタック

| 項目 | 技術 |
|------|------|
| フレームワーク | Next.js 15 (App Router) |
| 言語 | TypeScript (strict) |
| スタイル | Tailwind CSS 3 |
| 認証 | Supabase Auth (`@supabase/ssr`) |
| 決済 | Stripe Billing |
| ホスティング | Vercel |

## セットアップ

### 前提条件

- Node.js >= 18
- npm >= 9

### インストール

```bash
cd keiba/source
npm install
```

### 環境変数

`.env.example` をコピーして `.env.local` を作成し、実際の値を設定してください。

```bash
cp .env.example .env.local
```

| 変数名 | 用途 | 必須 |
|--------|------|:----:|
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase プロジェクト URL | ✓ |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon (public) key | ✓ |
| `STRIPE_SECRET_KEY` | Stripe シークレットキー | ✓ |
| `STRIPE_PRICE_ID` | プロプランの Stripe Price ID | ✓ |
| `STRIPE_WEBHOOK_SECRET` | Stripe Webhook 署名シークレット | ✓ |
| `NEXT_PUBLIC_APP_URL` | アプリの公開 URL | — |

> 環境変数が未設定の場合、起動時にコンソールへ warning が出力されます。

### 起動

```bash
npm run dev     # http://localhost:3000
npm run build   # 本番ビルド
npm run start   # 本番サーバー起動
```

## ディレクトリ構成

```
src/
├── app/                    # Next.js App Router ページ
│   ├── (auth)/             # 認証画面 (S01, S02)
│   ├── pricing/            # 料金プラン (S03)
│   ├── race/[id]/          # レース詳細 (S07)
│   ├── auth/callback/      # Supabase Auth コールバック
│   ├── api/stripe/checkout/ # Stripe Checkout セッション生成
│   ├── layout.tsx          # ルートレイアウト
│   ├── page.tsx            # レース一覧 (S04/S05/S06)
│   ├── error.tsx           # グローバルエラー境界
│   └── not-found.tsx       # 404 ページ
├── components/             # 共通 UI コンポーネント
│   ├── Header.tsx          # ヘッダー (状態別 CTA 切替)
│   ├── Footer.tsx
│   ├── Button.tsx
│   ├── Card.tsx
│   ├── Badge.tsx
│   ├── Tabs.tsx
│   └── LockedOverlay.tsx   # ロック表示 + ぼかし + CTA
├── features/               # 機能単位のコンポーネント群
│   ├── auth/               # AuthForm
│   ├── pricing/            # PricingCard
│   ├── race-list/          # RaceCard, RaceDateTabs, RaceListClient
│   ├── race-detail/        # (S07 拡張用)
│   └── plan-gating/        # policy.ts, UpgradeCta
├── lib/
│   ├── supabase/           # browser / server / middleware クライアント
│   ├── repositories/       # データアクセス境界 (mock / Supabase 切替)
│   ├── env.ts              # 環境変数バリデーション
│   └── logger.ts           # 環境別ログユーティリティ
├── types/                  # 共通型定義 (user, race)
├── mocks/                  # mock データ
└── middleware.ts            # セッション refresh
```

## 画面と状態の対応

| 画面ID | ルート | 説明 |
|--------|--------|------|
| S01 | `/signup` | 新規登録 |
| S02 | `/login` | ログイン |
| S03 | `/pricing` | 料金プラン |
| S04 | `/` | レース一覧 (通常) |
| S05 | `/` | レース一覧 (未ログインロック) |
| S06 | `/` | レース一覧 (期限切れロック) |
| S07 | `/race/[id]` | レース詳細 (ワイヤーフレーム) |

S04/S05/S06 は同一ページで、ユーザーの `UiState` に基づく `GatingPolicy` で表示を出し分けます。

## デバッグガイド

### 状態の確認

1. ブラウザの DevTools → Application → Cookies で Supabase セッション cookie を確認
2. Server Component 側のログは Vercel Functions ログ or ターミナル出力で確認
3. `lib/logger.ts` 経由のログは `[LEVEL][Tag] message` 形式で統一

### よくある問題

| 症状 | 確認箇所 |
|------|----------|
| ログイン後もロック表示 | `users` テーブルに `plan` レコードがあるか |
| Stripe Checkout が 503 | `.env.local` に `STRIPE_*` が設定されているか |
| middleware でリダイレクトループ | Supabase cookie の有効期限、`matcher` 設定 |
| 予測値が表示されない | `GatingPolicy` の `canViewPredictionValues` を確認 |

### Vercel Preview での確認

1. PR を push すると Preview URL が自動生成される
2. Vercel Dashboard → Settings → Environment Variables で Preview 用の値を設定
3. Functions タブでサーバーサイドログを確認

## 設計方針

- **SSOT**: `docs/` 配下の仕様書を正とする
- **Repository パターン**: `features/*` から直接 `supabase-js` を呼ばず、`lib/repositories` 経由
- **Policy パターン**: ロック表示は `derivePolicy()` で一元管理し、コンポーネントに課金ロジックを持たせない
- **Error Boundary**: app レベルの `error.tsx` でグローバル例外を捕捉
- **data-testid**: 主要 CTA に限定付与（将来の Playwright 導入を見据える）
