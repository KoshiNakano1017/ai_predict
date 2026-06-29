/** Supabase users.plan に格納される値 */
export type BackendPlan = "trial" | "expired" | "pro";
export type UserRole = "member" | "admin";

/**
 * UI 側で表示制御に使う 4 状態。
 * 03_認可設計.md §1.2 に準拠。
 */
export type UiState = "guest" | "trial" | "expired" | "pro";

export interface AppUser {
  id: string;
  email: string;
  plan: BackendPlan;
  role: UserRole;
  trialEndsAt: string | null;
}

/**
 * BackendPlan + ログイン有無 → UiState へ正規化する唯一の変換関数。
 * 03_認可設計.md §6「アプリ起動時の状態判定」に対応。
 *
 * 10_要件定義書.md §3.1.2:
 *   plan='trial' かつ trial_ends_at <= now() の場合は trial 期限切れとして扱う。
 *   DB の plan は バッチ/Cron で `expired` に降格する想定だが、降格までの
 *   タイムラグでも確実に制限が効くよう、フロント側でも判定する。
 *
 * `now` 引数はテスト容易性のために注入できるようにしている。
 */
export function deriveUiState(
  user: AppUser | null,
  now: Date = new Date(),
): UiState {
  if (!user) return "guest";

  if (user.plan === "trial" && user.trialEndsAt) {
    const endsAt = new Date(user.trialEndsAt);
    if (!Number.isNaN(endsAt.getTime()) && endsAt.getTime() <= now.getTime()) {
      return "expired";
    }
  }

  return user.plan;
}
