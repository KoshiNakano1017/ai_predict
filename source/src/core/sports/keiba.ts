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
    tagline: "1秒で買う馬を判断できる競馬AI",
    heroDescription:
      "レース映像データとAI分析をもとに、\n勝率と期待値を算出。\n「どの馬を買うべきか」を一瞬で判断できる競馬AIサービスです。",
    heroImageAlt: "競馬のレースイメージ",
    allEntries: "全頭",
    guestUnlockSummary: "全馬の勝率 / 期待値",
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
