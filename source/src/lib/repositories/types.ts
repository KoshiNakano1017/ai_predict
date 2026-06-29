import type { AppUser } from "@/types/user";
import type { EventSummary, RaceEvent, FeaturedInsights } from "@/types/race";

/**
 * データアクセスの境界インターフェース。
 * 初期は mock 実装、後で Supabase 実装に差し替える。
 */
export interface RaceRepository {
  getRaceList(date: string): Promise<EventSummary[]>;
  getRaceDetail(id: string): Promise<RaceEvent | null>;
  getFeaturedInsights(date: string): Promise<FeaturedInsights>;
  /**
   * データが投入されている最新の開催日 (YYYY-MM-DD) を返す。
   * データが無ければ null。日付セレクタのデフォルト値などに使う。
   */
  getLatestRaceDate(): Promise<string | null>;
  /**
   * データが投入されている開催日の一覧 (新しい順)。
   * 日付選択 UI で「実データがある日」だけ強調するなどに使う。
   */
  getAvailableRaceDates(): Promise<string[]>;
}

export interface UserRepository {
  getCurrentUser(): Promise<AppUser | null>;
}
