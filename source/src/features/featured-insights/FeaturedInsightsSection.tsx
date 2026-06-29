import type { FeaturedInsights } from "@/types/race";
import type { UiState } from "@/types/user";
import type { GatingPolicy } from "@/features/plan-gating/policy";
import { FeaturedKeyHorses } from "./FeaturedKeyHorses";
import { RiskyFavorites } from "./RiskyFavorites";
import { LongshotHorses } from "./LongshotHorses";

interface Props {
  /**
   * 03_認可設計 §2.1: プラン該当時のみ実データを渡す。
   * 権限がない場合は一部のデータのみが渡され、マスク UI を表示する。
   */
  insights: FeaturedInsights | null;
  uiState: UiState;
  policy: GatingPolicy;
}

export function FeaturedInsightsSection({ insights, uiState, policy }: Props) {
  const isLocked = !policy.canViewFeaturedInsights;

  return (
    <section className="space-y-4">
        <FeaturedKeyHorses
          items={insights?.keyCompetitors ?? null}
          uiState={uiState}
          locked={isLocked}
        />
        <div className="grid gap-4 md:grid-cols-2">
          <RiskyFavorites
            items={insights?.riskyFavorites ?? null}
            uiState={uiState}
            locked={isLocked}
          />
          <LongshotHorses
            items={insights?.longshots ?? null}
            uiState={uiState}
            locked={isLocked}
          />
        </div>
    </section>
  );
}
