import type { EventConditions } from "../domain";
import type { SportProfile } from "../sport-profile";

/**
 * 競艇（ボートレース）プロファイル。
 *
 * 1 レース 6 艇固定で着順を競い、進入コースが勝敗を大きく左右する。
 * 選手自身が操縦するため operator は使わない。
 */
export const kyoteiSport: SportProfile = {
  id: "kyotei",
  labels: {
    serviceName: "AI ボートレース予測",
    event: "レース",
    eventNumberSuffix: "R",
    venue: "競艇場",
    lane: "コース",
    bib: "艇番",
    competitor: "選手名",
    operator: "",
    odds: "オッズ",
    winRate: "勝率",
    placeRate: "2連対率",
    showRate: "3連対率",
    expectedValue: "期待値",
    reason: "理由",
    predictionTitle: "AI予想",
    entriesTitle: "全出走選手の詳細データ",
    featuredKeyTitle: "期待値の高い注目選手",
    riskyTitle: "危険な人気選手",
    longshotTitle: "高期待値の穴選手",
    recommended: "勝負",
    notRecommended: "見送り",
    tagline: "1秒で買う艇を判断できるボートレースAI",
    heroDescription:
      "レース映像データとAI分析をもとに、\n勝率と期待値を算出。\n「どの艇を買うべきか」を一瞬で判断できるボートレースAIサービスです。",
    heroImageAlt: "ボートレースのレースイメージ",
    allEntries: "全艇",
    guestUnlockSummary: "全艇の勝率 / 期待値",
  },
  ratings: {
    star: { icon: "★", label: "本命候補" },
    triangle: { icon: "▲", label: "高期待値選手" },
    caution: { icon: "⚠", label: "危険な人気選手" },
    darkHorse: { icon: "◆", label: "穴選手" },
  },
  formatConditions(conditions: EventConditions): string {
    return conditions.distanceMeters != null
      ? `${conditions.distanceMeters}m`
      : "";
  },
};
