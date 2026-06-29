/**
 * アクティブなスポーツプロファイルの解決。
 *
 * `NEXT_PUBLIC_SPORT` 環境変数で切り替える（既定は競艇）。
 * 競馬に戻す場合は NEXT_PUBLIC_SPORT=keiba を設定する。
 */
import type { SportId, SportProfile } from "./sport-profile";
import { keibaSport } from "./sports/keiba";
import { kyoteiSport } from "./sports/kyotei";

export type { SportId, SportProfile, RatingMeta, SportLabels } from "./sport-profile";

const SPORTS: Record<SportId, SportProfile> = {
  keiba: keibaSport,
  kyotei: kyoteiSport,
};

const DEFAULT_SPORT: SportId = "kyotei";

/** 現在のアクティブスポーツプロファイルを返す。 */
export function getActiveSport(): SportProfile {
  const id = process.env.NEXT_PUBLIC_SPORT as SportId | undefined;
  return (id && SPORTS[id]) || SPORTS[DEFAULT_SPORT];
}
