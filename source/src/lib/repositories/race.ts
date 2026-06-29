import type { RaceRepository } from "./types";
import {
  MOCK_RACE_CARDS,
  getMockRaceDetail,
  MOCK_FEATURED_INSIGHTS,
} from "@/mocks/races";
import { SupabaseRaceRepository } from "./race.supabase";

export class MockRaceRepository implements RaceRepository {
  async getRaceList(date: string) {
    // リクエストされた日付がモックデータの日付と一致しない場合は空を返す
    if (date !== MOCK_RACE_CARDS[0].date) {
      return [];
    }
    return [...MOCK_RACE_CARDS].sort((a, b) => {
      const v = a.venue.localeCompare(b.venue, "ja");
      if (v !== 0) return v;
      return a.eventNumber - b.eventNumber;
    });
  }

  async getRaceDetail(id: string) {
    return getMockRaceDetail(id);
  }

  async getFeaturedInsights(date: string) {
    if (date !== MOCK_RACE_CARDS[0].date) {
      return { keyCompetitors: [], riskyFavorites: [], longshots: [] };
    }
    return MOCK_FEATURED_INSIGHTS;
  }

  async getLatestRaceDate() {
    // mock 用の固定値: 既存サンプルが日付に依存しないため一律で返す
    return MOCK_RACE_CARDS[0]?.date ?? null;
  }

  async getAvailableRaceDates() {
    const dates = MOCK_RACE_CARDS.map((r) => r.date);
    return Array.from(new Set(dates)).sort((a, b) => b.localeCompare(a));
  }
}

/**
 * リポジトリのファクトリ関数。
 *
 * NEXT_PUBLIC_USE_REAL_DATA=true の場合は Supabase 実装を返す。
 * それ以外 (ローカル開発・Vercel Preview でデータ未投入時) は Mock を返す。
 */
export function createRaceRepository(): RaceRepository {
  if (process.env.NEXT_PUBLIC_USE_REAL_DATA === "true") {
    return new SupabaseRaceRepository();
  }
  return new MockRaceRepository();
}
