/**
 * Supabase 実装の RaceRepository。
 *
 * バッチが投入した races / entries テーブルから読み取る。
 * Server Component (RSC) 側から呼ばれる前提で createClient() (server.ts) を使用する。
 */
import type { RaceRepository } from "./types";
import type {
  RaceEvent,
  EventSummary,
  Competitor,
  FeaturedInsights,
  KeyCompetitor,
  RiskyFavorite,
  Longshot,
} from "@/types/race";
import { createClient } from "@/lib/supabase/server";
import { getActiveSport } from "@/core/sport";

const sport = getActiveSport();

// ──────────────────────────────────────────────────────────────────────────────
// DB 行型 (003_create_races_entries.sql の列に対応)
// ──────────────────────────────────────────────────────────────────────────────
interface DbRace {
  race_key: string;
  target_date: string;
  venue: string;
  race_no: number;
  track_type: string | null;
  race_distance: number | null;
  start_time: string | null;
  num_horses: number | null;
}

interface DbEntry {
  entry_key: string;
  race_key: string;
  frame_number: number | null;
  horse_number: number;
  horse_name: string | null;
  jockey_name: string | null;
  win_odds: number | null;
  star_rating: "★" | "▲" | "⚠" | "◆" | null;
  win_rate: number | null;
  place_rate: number | null;
  show_rate: number | null;
  expected_value_win: number | null;
  expected_value_place: number | null;
  popularity_rank: number | null;
  ai_comment: string | null;
}

// ──────────────────────────────────────────────────────────────────────────────
// マッピングヘルパー
// ──────────────────────────────────────────────────────────────────────────────
function mapEntry(row: DbEntry): Competitor {
  return {
    lane: row.frame_number ?? null,
    bib: row.horse_number,
    name: row.horse_name ?? "",
    operator: row.jockey_name ?? null,
    odds: row.win_odds ?? 0,
    rating: row.star_rating ?? null,
    winRate: row.win_rate ?? null,
    placeRate: row.place_rate ?? null,
    showRate: row.show_rate ?? null,
    expectedValue: row.expected_value_win ?? null,
    reason: row.ai_comment ?? null,
    tags: [],
  };
}

function mapConditions(dbRace: DbRace) {
  return {
    distanceMeters: dbRace.race_distance ?? null,
    surface: dbRace.track_type ?? null,
  };
}

function mapRace(dbRace: DbRace, entries: DbEntry[]): RaceEvent {
  return {
    id: dbRace.race_key,
    title: `${dbRace.venue}${dbRace.race_no}R`,
    venue: dbRace.venue,
    eventNumber: dbRace.race_no,
    date: dbRace.target_date,
    startTime: dbRace.start_time ?? "",
    conditions: mapConditions(dbRace),
    competitors: entries
      .sort((a, b) => a.horse_number - b.horse_number)
      .map(mapEntry),
  };
}

function mapRaceCard(dbRace: DbRace, entries: DbEntry[]): EventSummary {
  const star = entries.find((e) => e.star_rating === "★");
  const triangle = entries.find((e) => e.star_rating === "▲");
  const caution = entries.find((e) => e.star_rating === "⚠");
  const darkHorse = entries.find((e) => e.star_rating === "◆");

  return {
    id: dbRace.race_key,
    title: `${dbRace.venue}${dbRace.race_no}R`,
    venue: dbRace.venue,
    eventNumber: dbRace.race_no,
    date: dbRace.target_date,
    startTime: dbRace.start_time ?? "",
    conditions: mapConditions(dbRace),
    topPicks: {
      star: star ? { name: star.horse_name ?? "", winRate: star.win_rate ?? null, expectedValue: star.expected_value_win ?? null } : null,
      triangle: triangle ? { name: triangle.horse_name ?? "", winRate: triangle.win_rate ?? null, expectedValue: triangle.expected_value_win ?? null } : null,
      caution: caution ? { name: caution.horse_name ?? "" } : null,
      darkHorse: darkHorse ? { name: darkHorse.horse_name ?? "" } : null,
    },
  };
}

// ──────────────────────────────────────────────────────────────────────────────
// SupabaseRaceRepository
// ──────────────────────────────────────────────────────────────────────────────
export class SupabaseRaceRepository implements RaceRepository {
  async getRaceList(date: string): Promise<EventSummary[]> {
    const supabase = await createClient();

    const { data: races, error: raceErr } = await supabase
      .from("races")
      .select("race_key, target_date, venue, race_no, track_type, race_distance, start_time, num_horses")
      .eq("target_date", date)
      .order("race_no");

    console.log(`[SSR] getRaceList fetched ${races?.length || 0} races for ${date}`);

    if (raceErr) throw new Error(`races 取得エラー: ${raceErr.message}`);
    if (!races || races.length === 0) return [];

    const raceKeys = races.map((r) => r.race_key);

    const { data: entries, error: entryErr } = await supabase
      .from("entries")
      .select(
        "entry_key, race_key, horse_number, horse_name, jockey_name, win_odds, star_rating, win_rate, place_rate, show_rate, expected_value_win, expected_value_place, popularity_rank"
      )
      .in("race_key", raceKeys);

    if (entryErr) throw new Error(`entries 取得エラー: ${entryErr.message}`);

    const entriesByRace = groupBy(entries ?? [], (e) => e.race_key);

    return (races as DbRace[]).map((r) =>
      mapRaceCard(r, (entriesByRace[r.race_key] ?? []) as DbEntry[])
    );
  }

  async getRaceDetail(id: string): Promise<RaceEvent | null> {
    const supabase = await createClient();

    const { data: race, error: raceErr } = await supabase
      .from("races")
      .select("race_key, target_date, venue, race_no, track_type, race_distance, start_time, num_horses")
      .eq("race_key", id)
      .single();

    if (raceErr) {
      if (raceErr.code === "PGRST116") return null; // not found
      throw new Error(`race 取得エラー: ${raceErr.message}`);
    }
    if (!race) return null;

    const { data: entries, error: entryErr } = await supabase
      .from("entries")
      .select(
        "entry_key, race_key, frame_number, horse_number, horse_name, jockey_name, win_odds, star_rating, win_rate, place_rate, show_rate, expected_value_win, expected_value_place, popularity_rank, ai_comment"
      )
      .eq("race_key", id)
      .order("horse_number");

    if (entryErr) throw new Error(`entries 取得エラー: ${entryErr.message}`);

    return mapRace(race as DbRace, (entries ?? []) as DbEntry[]);
  }

  async getLatestRaceDate(): Promise<string | null> {
    const supabase = await createClient();
    const { data, error } = await supabase
      .from("races")
      .select("target_date")
      // 今日以前の日付の中で最新のものを取得する (未来のデータは無視)
      // JSTの今日の日付を基準にする
      .lte("target_date", new Date(Date.now() + ((new Date().getTimezoneOffset() + (9 * 60)) * 60 * 1000)).toISOString().slice(0, 10))
      .order("target_date", { ascending: false })
      .limit(1);
    if (error) {
      console.error(`getLatestRaceDate error:`, error);
      return null;
    }
    if (!data || data.length === 0) return null;
    return data[0].target_date as string;
  }

  async getAvailableRaceDates(): Promise<string[]> {
    const supabase = await createClient();
    const { data, error } = await supabase
      .from("races")
      .select("target_date")
      .order("target_date", { ascending: false });
    if (error) throw new Error(`getAvailableRaceDates error: ${error.message}`);
    if (!data) return [];
    // distinct を SQL で取れないので JS 側でユニーク化
    const seen = new Set<string>();
    const result: string[] = [];
    for (const row of data as { target_date: string }[]) {
      if (!seen.has(row.target_date)) {
        seen.add(row.target_date);
        result.push(row.target_date);
      }
    }
    return result;
  }

  async getFeaturedInsights(date: string): Promise<FeaturedInsights> {
    const supabase = await createClient();

    const { data: races, error: raceErr } = await supabase
      .from("races")
      .select("race_key, venue, race_no")
      .eq("target_date", date);

    if (raceErr) throw new Error(`races 取得エラー: ${raceErr.message}`);
    if (!races || races.length === 0) {
      return { keyCompetitors: [], riskyFavorites: [], longshots: [] };
    }

    const raceKeys = races.map((r) => r.race_key);
    const raceMap = Object.fromEntries(
      races.map((r) => [r.race_key, { venue: r.venue, eventNumber: r.race_no }])
    );

    const { data: entries, error: entryErr } = await supabase
      .from("entries")
      .select(
        "race_key, horse_name, star_rating, win_rate, expected_value_win, ai_comment, popularity_rank"
      )
      .in("race_key", raceKeys)
      .in("star_rating", ["★", "▲", "⚠", "◆"]);

    if (entryErr) throw new Error(`entries 取得エラー: ${entryErr.message}`);

    const keyCompetitors: KeyCompetitor[] = [];
    const riskyFavorites: RiskyFavorite[] = [];
    const longshots: Longshot[] = [];

    for (const e of entries ?? []) {
      const meta = raceMap[e.race_key];
      if (!meta) continue;

      if (e.star_rating === "★" || e.star_rating === "▲") {
        keyCompetitors.push({
          rank: e.star_rating === "★" ? 1 : 2,
          name: e.horse_name ?? "",
          eventId: e.race_key,
          venue: meta.venue,
          eventNumber: meta.eventNumber,
          winRate: e.win_rate ?? 0,
          expectedValue: e.expected_value_win ?? 0,
          comment: e.ai_comment ?? "",
        });
      }
      if (e.star_rating === "⚠") {
        riskyFavorites.push({
          eventId: e.race_key,
          venue: meta.venue,
          eventNumber: meta.eventNumber,
          name: e.horse_name ?? "",
          reason: e.ai_comment ?? sport.ratings.caution.label,
        });
      }
      if (e.star_rating === "◆") {
        longshots.push({
          eventId: e.race_key,
          venue: meta.venue,
          eventNumber: meta.eventNumber,
          name: e.horse_name ?? "",
          expectedValue: e.expected_value_win ?? 0,
        });
      }
    }

    // 期待値降順でソートし、各カテゴリ上位 N 件のみをフロントに渡す。
    // keyCompetitors は ★/▲ 由来でランクが 1/2 に偏るため、
    // ソート後の順位で 1..N の連番ランクを振り直して UI のバッジ表示を整える。
    keyCompetitors.sort((a, b) => b.expectedValue - a.expectedValue);
    longshots.sort((a, b) => b.expectedValue - a.expectedValue);

    const FEATURED_LIMIT = 5;

    return {
      keyCompetitors: keyCompetitors
        .slice(0, FEATURED_LIMIT)
        .map((h, i) => ({ ...h, rank: i + 1 })),
      riskyFavorites: riskyFavorites.slice(0, FEATURED_LIMIT),
      longshots: longshots.slice(0, FEATURED_LIMIT),
    };
  }
}

// ──────────────────────────────────────────────────────────────────────────────
// ユーティリティ
// ──────────────────────────────────────────────────────────────────────────────
function groupBy<T>(arr: T[], keyFn: (item: T) => string): Record<string, T[]> {
  return arr.reduce<Record<string, T[]>>((acc, item) => {
    const k = keyFn(item);
    (acc[k] ??= []).push(item);
    return acc;
  }, {});
}
