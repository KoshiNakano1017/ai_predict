/**
 * スポーツプロファイル（競技アダプタ）の型定義。
 *
 * 競技固有の「呼称」「条件の表示整形」「評価マークの意味」をここに集約する。
 * UI コンポーネントはドメイン型（core/domain.ts）と本プロファイルのみに依存し、
 * 競技名や「馬」などの固有語をハードコードしない。
 */
import type { EventConditions } from "./domain";

export type SportId = "keiba" | "kyotei";

/** 評価マーク（★▲⚠◆）の表示メタ。 */
export interface RatingMeta {
  icon: string;
  label: string;
}

/** UI 文言の集合。競技ごとに差し替える。 */
export interface SportLabels {
  /** サービス表示名。 */
  serviceName: string;
  /** 「レース」に相当する語。 */
  event: string;
  /** レース番号の接尾辞（例: "R"）。 */
  eventNumberSuffix: string;
  /** 開催地（競馬場・競艇場など）。 */
  venue: string;
  /** 進入位置（枠・コース）。 */
  lane: string;
  /** 出走番号（馬番・艇番）。 */
  bib: string;
  /** 競争者（馬名・選手名）。 */
  competitor: string;
  /** 操縦者（騎手など）。無い競技では空文字でよい。 */
  operator: string;
  odds: string;
  winRate: string;
  placeRate: string;
  showRate: string;
  expectedValue: string;
  reason: string;
  /** AI 予想セクションの見出し。 */
  predictionTitle: string;
  /** 出走表セクションの見出し。 */
  entriesTitle: string;
  /** 注目競争者サマリーの見出し。 */
  featuredKeyTitle: string;
  /** 危険人気サマリーの見出し。 */
  riskyTitle: string;
  /** 高期待値穴サマリーの見出し。 */
  longshotTitle: string;
  /** 「注目」バッジ。 */
  recommended: string;
  /** 「見送り」バッジ。 */
  notRecommended: string;
  /** 認証画面・ヒーローのキャッチコピー。 */
  tagline: string;
  /** ヒーローセクションの説明文。 */
  heroDescription: string;
  /** ヒーロー画像の alt テキスト。 */
  heroImageAlt: string;
  /** 料金プラン等の「全○」表記（例: 全頭 / 全艇）。 */
  allEntries: string;
  /** 未ログイン CTA の解放機能説明。 */
  guestUnlockSummary: string;
}

export interface SportProfile {
  id: SportId;
  labels: SportLabels;
  ratings: Record<"star" | "triangle" | "caution" | "darkHorse", RatingMeta>;
  /** 開催条件を表示用文字列に整形する（例: "芝1500m" / "1800m"）。 */
  formatConditions(conditions: EventConditions): string;
}
