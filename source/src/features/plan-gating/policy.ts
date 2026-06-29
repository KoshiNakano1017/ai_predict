import type { UiState } from "@/types/user";

/**
 * 03_認可設計.md §2.1 段階ロック設計の画面前提に準拠。
 *
 * 暫定ルール（feature flag として差し替え可能）:
 *   guest / expired → ★ ▲ は表示、⚠ ◆ はマスク
 *   trial / pro     → 全表示
 */
export interface GatingPolicy {
  canViewStar: boolean;
  canViewTriangle: boolean;
  canViewCaution: boolean;
  canViewDarkHorse: boolean;
  canViewPredictionValues: boolean;
  /** ホーム上部の期待値注目馬・危険人気馬・高期待値穴馬の表示可否 */
  canViewFeaturedInsights: boolean;
  showLoginCta: boolean;
  showUpgradeCta: boolean;
  showTrialBanner: boolean;
  trialDaysLeft: number | null;
}

export function derivePolicy(
  uiState: UiState,
  trialEndsAt: string | null,
): GatingPolicy {
  const base = {
    canViewStar: true,
    canViewTriangle: true,
    trialDaysLeft: null,
  };

  switch (uiState) {
    case "guest":
      return {
        ...base,
        canViewCaution: false,
        canViewDarkHorse: false,
        canViewPredictionValues: false,
        canViewFeaturedInsights: false,
        showLoginCta: true,
        showUpgradeCta: false,
        showTrialBanner: false,
      };

    case "trial": {
      const days = trialEndsAt
        ? Math.max(
            0,
            Math.ceil(
              (new Date(trialEndsAt).getTime() - Date.now()) / 86400000,
            ),
          )
        : null;
      return {
        ...base,
        canViewCaution: true,
        canViewDarkHorse: true,
        canViewPredictionValues: true,
        canViewFeaturedInsights: true,
        showLoginCta: false,
        showUpgradeCta: false,
        showTrialBanner: true,
        trialDaysLeft: days,
      };
    }

    case "expired":
      return {
        ...base,
        canViewCaution: false,
        canViewDarkHorse: false,
        canViewPredictionValues: false,
        canViewFeaturedInsights: false,
        showLoginCta: false,
        showUpgradeCta: true,
        showTrialBanner: false,
      };

    case "pro":
      return {
        ...base,
        canViewCaution: true,
        canViewDarkHorse: true,
        canViewPredictionValues: true,
        canViewFeaturedInsights: true,
        showLoginCta: false,
        showUpgradeCta: false,
        showTrialBanner: false,
      };
  }
}
