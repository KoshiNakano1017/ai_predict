/**
 * レース系ドメイン型のバレル。
 *
 * 実体はスポーツ非依存のコアドメイン（@/core/domain）にあり、ここから再公開する。
 * 競技固有の呼称・表示は @/core/sport の SportProfile が解決する。
 */
export type {
  Rating,
  EventConditions,
  Competitor,
  TopPick,
  RaceEvent,
  EventSummary,
  KeyCompetitor,
  RiskyFavorite,
  Longshot,
  FeaturedInsights,
} from "@/core/domain";
