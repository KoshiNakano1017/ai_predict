/**
 * スポーツ非依存の「レース型（多競争者・着順）」コアドメインモデル。
 *
 * 競馬・競艇・競輪・F1 などの「1イベントに N 競争者が出走し着順を競う」競技を
 * 共通の型で扱う。競技固有の呼称（枠/コース・馬番/艇番・馬名/選手名 等）は
 * `SportProfile`（core/sport-profile.ts）が表示時に解決する。
 */

/** 着順評価マーク。各競技の本命/対抗/危険人気/穴へマッピングされる。 */
export type Rating = "★" | "▲" | "⚠" | "◆";

/**
 * レースの開催条件。競技ごとに意味づけは `SportProfile.formatConditions` が解釈する。
 * 例) 競馬: surface="芝", distanceMeters=1500 / 競艇: surface=null, distanceMeters=1800
 */
export interface EventConditions {
  /** 距離 (m)。取得できない競技・データでは null。 */
  distanceMeters: number | null;
  /** 路面・水面などの種別 (芝/ダート 等)。無い競技では null。 */
  surface: string | null;
}

/** 1 レースに出走する 1 競争者（馬・艇・選手など）。 */
export interface Competitor {
  /** 進入位置（枠番・コースなど）。無い競技では null。 */
  lane: number | null;
  /** 出走番号（馬番・艇番など）。レース内で一意。 */
  bib: number;
  /** 競争者名（馬名・選手名など）。 */
  name: string;
  /** 操縦者（騎手など）。競争者自身が操縦する競技（競艇等）では null。 */
  operator: string | null;
  /** 単勝オッズ。 */
  odds: number;
  /** AI 評価マーク。 */
  rating: Rating | null;
  /** 予想勝率 (0-100)。 */
  winRate: number | null;
  /** 予想連対率 (0-100)。 */
  placeRate: number | null;
  /** 予想複勝率 (0-100)。 */
  showRate: number | null;
  /** 期待値 (%)。 */
  expectedValue: number | null;
  /** AI 評価理由。 */
  reason: string | null;
  /** 評価根拠の短いタグ。 */
  tags: string[];
}

/** 1 レース（出走表つきの詳細）。 */
export interface RaceEvent {
  id: string;
  /** レース名（例: メイン特別）。 */
  title: string;
  /** 開催地（競馬場・競艇場など）。 */
  venue: string;
  /** レース番号（1R, 2R...）。 */
  eventNumber: number;
  /** 開催日 (YYYY-MM-DD)。 */
  date: string;
  /** 発走時刻 (HH:MM)。 */
  startTime: string;
  conditions: EventConditions;
  competitors: Competitor[];
}

/** 一覧カードに表示する上位ピックの最小情報。 */
export interface TopPick {
  name: string;
  winRate: number | null;
  expectedValue: number | null;
}

/** レース一覧用のサマリーカード（出走表は持たない）。 */
export interface EventSummary {
  id: string;
  title: string;
  venue: string;
  eventNumber: number;
  date: string;
  startTime: string;
  conditions: EventConditions;
  topPicks: {
    star: TopPick | null;
    triangle: TopPick | null;
    caution: { name: string } | null;
    darkHorse: { name: string } | null;
  };
}

/** 期待値の高い注目競争者（ホーム上部サマリー用）。 */
export interface KeyCompetitor {
  rank: number;
  name: string;
  /** 遷移先レースの ID。 */
  eventId: string;
  venue: string;
  eventNumber: number;
  /** 予想勝率 0-100。 */
  winRate: number;
  /** 期待値 %（+が良い）。 */
  expectedValue: number;
  comment: string;
}

/** 危険な人気（過剰人気だが期待値が低い）。 */
export interface RiskyFavorite {
  eventId: string;
  venue: string;
  eventNumber: number;
  name: string;
  reason: string;
}

/** 高期待値の穴（人気薄だが期待値が高い）。 */
export interface Longshot {
  eventId: string;
  venue: string;
  eventNumber: number;
  name: string;
  /** 期待値 %（+が良い）。 */
  expectedValue: number;
}

/** ホーム上部の注目サマリー集合（プラン別表示制御の対象）。 */
export interface FeaturedInsights {
  keyCompetitors: KeyCompetitor[];
  riskyFavorites: RiskyFavorite[];
  longshots: Longshot[];
}
