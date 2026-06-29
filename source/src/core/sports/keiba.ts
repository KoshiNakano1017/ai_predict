import type { EventConditions } from "../domain";
import type { SportProfile } from "../sport-profile";

/** 競馬（JRA）プロファイル。 */
export const keibaSport: SportProfile = {
  id: "keiba",
  labels: {
    serviceName: "CrossFactor AI 競馬予測",
    event: "レース",
    eventNumberSuffix: "R",
    venue: "競馬場",
    lane: "枠",
    bib: "馬番",
    competitor: "馬名",
    operator: "騎手",
    odds: "オッズ",
    winRate: "勝率",
    placeRate: "連対率",
    showRate: "複勝率",
    expectedValue: "期待値",
    reason: "理由",
    predictionTitle: "AI予想",
    entriesTitle: "全出走馬の詳細データ",
    featuredKeyTitle: "期待値の高い注目馬",
    riskyTitle: "危険な人気馬",
    longshotTitle: "高期待値穴馬",
    recommended: "注目",
    notRecommended: "見送り",
  },
  ratings: {
    star: { icon: "★", label: "本命候補" },
    triangle: { icon: "▲", label: "高期待値馬" },
    caution: { icon: "⚠", label: "危険な人気馬" },
    darkHorse: { icon: "◆", label: "穴馬" },
  },
  formatConditions(conditions: EventConditions): string {
    const surface = conditions.surface ?? "";
    const distance =
      conditions.distanceMeters != null ? `${conditions.distanceMeters}m` : "";
    return `${surface}${distance}`;
  },
};
