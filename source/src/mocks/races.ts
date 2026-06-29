import type {
  EventSummary,
  RaceEvent,
  Competitor,
  FeaturedInsights,
} from "@/types/race";
import { getActiveSport } from "@/core/sport";

const today = new Date().toISOString().slice(0, 10);
const sport = getActiveSport();

// ──────────────────────────────────────────────────────────────────────────────
// 競馬 (Keiba) モックデータ
// ──────────────────────────────────────────────────────────────────────────────

const KEIBA_VENUES = [
  { venue: "中山", prefix: "nakayama" },
  { venue: "阪神", prefix: "hanshin" },
  { venue: "中京", prefix: "chukyo" },
] as const;

function buildExtraKeibaRaces(
  venue: string,
  prefix: string,
  from: number,
  to: number,
): EventSummary[] {
  const races: EventSummary[] = [];
  for (let eventNumber = from; eventNumber <= to; eventNumber++) {
    const surface = eventNumber % 2 === 0 ? "芝" : "ダート";
    const distance = eventNumber <= 6 ? 1200 + eventNumber * 100 : 1600 + (eventNumber - 6) * 200;
    const highEv = eventNumber % 4 === 0;
    races.push({
      id: `race-${prefix}-${eventNumber}r`,
      title:
        eventNumber >= 11
          ? "メイン特別"
          : eventNumber >= 8
            ? "4歳上1勝"
            : "3歳未勝利",
      venue,
      eventNumber,
      date: today,
      startTime: `${9 + Math.floor(eventNumber / 2)}:${eventNumber % 2 === 0 ? "30" : "00"}`,
      conditions: { distanceMeters: distance, surface },
      topPicks: {
        star: {
          name: `${venue}スター${eventNumber}`,
          winRate: 18 + eventNumber,
          expectedValue: highEv ? 12.5 : 4.2,
        },
        triangle: {
          name: `${venue}アロー${eventNumber}`,
          winRate: 15 + eventNumber,
          expectedValue: highEv ? 14.9 : 6.1,
        },
        caution:
          eventNumber % 3 === 0
            ? { name: `${venue}危険${eventNumber}` }
            : null,
        darkHorse:
          eventNumber % 5 === 0
            ? { name: `${venue}穴${eventNumber}` }
            : null,
      },
    });
  }
  return races;
}

const BASE_KEIBA_DATA: EventSummary[] = [
  {
    id: "race-nakayama-1r",
    title: "3歳未勝利",
    venue: "中山",
    eventNumber: 1,
    date: today,
    startTime: "09:50",
    conditions: { distanceMeters: 1500, surface: "芝" },
    topPicks: {
      star: { name: "マリンブルー", winRate: 28, expectedValue: 8.2 },
      triangle: { name: "コーラルリーフ", winRate: 22, expectedValue: 9.5 },
      caution: { name: "ダンジャーポップ" },
      darkHorse: { name: "ミステリーウィン" },
    },
  },
];

const KEIBA_INSIGHTS: FeaturedInsights = {
  keyCompetitors: [
    {
      rank: 1,
      name: "ロイヤルプリンス",
      eventId: "race-nakayama-10r",
      venue: "中山",
      eventNumber: 10,
      winRate: 40,
      expectedValue: 22.8,
      comment: "展開が向きやすく好条件",
    },
    {
      rank: 2,
      name: "エースファイター",
      eventId: "race-nakayama-9r",
      venue: "中山",
      eventNumber: 9,
      winRate: 38,
      expectedValue: 18.5,
      comment: "距離適性が高く安定感あり",
    },
    {
      rank: 3,
      name: "ダークホース",
      eventId: "race-chukyo-10r",
      venue: "中京",
      eventNumber: 10,
      winRate: 35,
      expectedValue: 15.2,
      comment: "距離適性が高く安定感あり",
    },
    {
      rank: 4,
      name: "サンライズクイーン",
      eventId: "race-hanshin-10r",
      venue: "阪神",
      eventNumber: 10,
      winRate: 32,
      expectedValue: 12.3,
      comment: "前走内容良好で期待大",
    },
    {
      rank: 5,
      name: "オーシャンブルー",
      eventId: "race-hanshin-9r",
      venue: "阪神",
      eventNumber: 9,
      winRate: 30,
      expectedValue: 10.7,
      comment: "前走内容良好で期待大",
    },
  ],
  riskyFavorites: [
    { eventId: "race-nakayama-11r", venue: "中山", eventNumber: 11, name: "スプリントキング", reason: "展開不利" },
    { eventId: "race-hanshin-11r", venue: "阪神", eventNumber: 11, name: "ファイナルアンサー", reason: "人気先行で妙味薄" },
    { eventId: "race-chukyo-11r", venue: "中京", eventNumber: 11, name: "トップレート", reason: "斤量増で割引" },
  ],
  longshots: [
    { eventId: "race-hanshin-7r", venue: "阪神", eventNumber: 7, name: "グリーンフラッシュ", expectedValue: 15.5 },
    { eventId: "race-chukyo-12r", venue: "中京", eventNumber: 12, name: "ミッドナイトスター", expectedValue: 13.4 },
    { eventId: "race-nakayama-8r", venue: "中山", eventNumber: 8, name: "アンダードッグ", expectedValue: 11.2 },
  ],
};

// ──────────────────────────────────────────────────────────────────────────────
// 競艇 (Kyotei) モックデータ
// ──────────────────────────────────────────────────────────────────────────────

const KYOTEI_VENUES = [
  { venue: "平和島", prefix: "heiwajima" },
  { venue: "住之江", prefix: "suminoe" },
  { venue: "福岡", prefix: "fukuoka" },
] as const;

const BOAT_RACERS = ["峰竜太", "毒島誠", "桐生順平", "馬場貴也", "石野貴之", "茅原悠紀", "菊地孝平", "濱野谷憲吾", "西山貴浩", "平山智加"];

function buildExtraKyoteiRaces(
  venue: string,
  prefix: string,
  from: number,
  to: number,
): EventSummary[] {
  const races: EventSummary[] = [];
  for (let eventNumber = from; eventNumber <= to; eventNumber++) {
    const highEv = eventNumber % 4 === 0;
    races.push({
      id: `race-${prefix}-${eventNumber}r`,
      title: eventNumber === 12 ? "優勝戦" : eventNumber >= 10 ? "特別選抜戦" : "予選",
      venue,
      eventNumber,
      date: today,
      startTime: `${10 + Math.floor(eventNumber / 2)}:${eventNumber % 2 === 0 ? "30" : "00"}`,
      conditions: { distanceMeters: 1800, surface: null },
      topPicks: {
        star: {
          name: BOAT_RACERS[eventNumber % BOAT_RACERS.length],
          winRate: 45 + (6 - (eventNumber % 6)),
          expectedValue: highEv ? 15.2 : 5.8,
        },
        triangle: {
          name: BOAT_RACERS[(eventNumber + 1) % BOAT_RACERS.length],
          winRate: 35 + (eventNumber % 5),
          expectedValue: highEv ? 12.4 : 8.1,
        },
        caution: eventNumber % 3 === 0 ? { name: BOAT_RACERS[(eventNumber + 2) % BOAT_RACERS.length] } : null,
        darkHorse: eventNumber % 5 === 0 ? { name: BOAT_RACERS[(eventNumber + 3) % BOAT_RACERS.length] } : null,
      },
    });
  }
  return races;
}

const BASE_KYOTEI_DATA: EventSummary[] = [
  {
    id: "race-heiwajima-1r",
    title: "予選",
    venue: "平和島",
    eventNumber: 1,
    date: today,
    startTime: "10:30",
    conditions: { distanceMeters: 1800, surface: null },
    topPicks: {
      star: { name: "峰竜太", winRate: 58.2, expectedValue: 12.5 },
      triangle: { name: "毒島誠", winRate: 42.1, expectedValue: 9.8 },
      caution: { name: "石野貴之" },
      darkHorse: { name: "西山貴浩" },
    },
  },
];

const KYOTEI_INSIGHTS: FeaturedInsights = {
  keyCompetitors: [
    {
      rank: 1,
      name: "峰竜太",
      eventId: "race-suminoe-12r",
      venue: "住之江",
      eventNumber: 12,
      winRate: 65,
      expectedValue: 25.4,
      comment: "1コースからの逃げ濃厚。機力も節一クラス。",
    },
    {
      rank: 2,
      name: "馬場貴也",
      eventId: "race-fukuoka-12r",
      venue: "福岡",
      eventNumber: 12,
      winRate: 58,
      expectedValue: 18.2,
      comment: "3コースからのまくり差しに定評あり。旋回スピード抜群。",
    },
  ],
  riskyFavorites: [
    { eventId: "race-heiwajima-11r", venue: "平和島", eventNumber: 11, name: "毒島誠", reason: "機力不足でイン逃げ疑問" },
  ],
  longshots: [
    { eventId: "race-suminoe-8r", venue: "住之江", eventNumber: 8, name: "西山貴浩", expectedValue: 15.8 },
  ],
};

// ──────────────────────────────────────────────────────────────────────────────
// 切り替えロジック
// ──────────────────────────────────────────────────────────────────────────────

export const MOCK_RACE_CARDS: EventSummary[] =
  sport.id === "kyotei"
    ? [
        ...BASE_KYOTEI_DATA,
        ...KYOTEI_VENUES.flatMap(({ venue, prefix }) => buildExtraKyoteiRaces(venue, prefix, 2, 12)),
      ]
    : [
        ...BASE_KEIBA_DATA,
        ...KEIBA_VENUES.flatMap(({ venue, prefix }) =>
          buildExtraKeibaRaces(venue, prefix, venue === "中山" ? 2 : 1, 12)
        ),
      ];

export const MOCK_FEATURED_INSIGHTS: FeaturedInsights =
  sport.id === "kyotei" ? KYOTEI_INSIGHTS : KEIBA_INSIGHTS;

// ──────────────────────────────────────────────────────────────────────────────
// 詳細生成ロジック
// ──────────────────────────────────────────────────────────────────────────────

function buildKeibaCompetitor(num: number, total: number, partial: any, odds: number): Competitor {
  const laneOf = (bib: number, t: number) => (t <= 8 ? bib : (16 - t) + Math.ceil((bib - (16 - t)) / 2)); // 簡易版
  const OPERATORS = ["武豊", "ルメール", "川田", "松山", "横山武", "戸崎", "福永", "池添", "岩田望", "三浦"];
  return {
    lane: num <= total ? (total <= 8 ? num : Math.ceil(num / 2)) : null, // 枠
    bib: num,
    name: partial.name,
    operator: OPERATORS[(num - 1) % OPERATORS.length],
    odds,
    rating: partial.rating,
    winRate: partial.winRate,
    placeRate: partial.winRate ? partial.winRate * 1.5 : null,
    showRate: partial.winRate ? partial.winRate * 2.0 : null,
    expectedValue: partial.expectedValue,
    reason: partial.reason,
    tags: partial.tags || [],
  };
}

function buildKyoteiCompetitor(num: number, total: number, partial: any, odds: number): Competitor {
  return {
    lane: num, // 競艇では 1-6 コースが基本（進入固定想定）
    bib: num,  // 1-6 艇
    name: partial.name || BOAT_RACERS[(num - 1) % BOAT_RACERS.length],
    operator: null, // 競艇に騎手はいない
    odds,
    rating: partial.rating,
    winRate: partial.winRate || (num === 1 ? 50 : 10),
    placeRate: partial.winRate ? partial.winRate * 1.2 : null,
    showRate: partial.winRate ? partial.winRate * 1.5 : null,
    expectedValue: partial.expectedValue,
    reason: partial.reason || "機力、スタート共に安定。上位争い必至。",
    tags: partial.tags || [],
  };
}

export function getMockRaceDetail(id: string): RaceEvent | null {
  const card = MOCK_RACE_CARDS.find((c) => c.id === id);
  if (!card) return null;

  const total = sport.id === "kyotei" ? 6 : 10;
  const competitors: Competitor[] = [];
  
  for (let num = 1; num <= total; num++) {
    const isStar = num === (sport.id === "kyotei" ? 1 : 5);
    const isTriangle = num === (sport.id === "kyotei" ? 3 : 3);
    const isCaution = num === (sport.id === "kyotei" ? 2 : 1);
    const isDark = num === (sport.id === "kyotei" ? 4 : 8);

    const partial: any = {
      name: isStar ? card.topPicks.star?.name :
            isTriangle ? card.topPicks.triangle?.name :
            isCaution ? card.topPicks.caution?.name :
            isDark ? card.topPicks.darkHorse?.name : null,
      rating: isStar ? "★" : isTriangle ? "▲" : isCaution ? "⚠" : isDark ? "◆" : null,
      winRate: isStar ? card.topPicks.star?.winRate : isTriangle ? card.topPicks.triangle?.winRate : null,
      expectedValue: isStar ? card.topPicks.star?.expectedValue : isTriangle ? card.topPicks.triangle?.expectedValue : null,
      reason: isStar ? (sport.id === "kyotei" ? "イン速攻の期待大。壁も厚く逃げ切りが濃厚。" : "実力最上位。") : null,
      tags: isStar ? (sport.id === "kyotei" ? ["逃げ信頼", "機力上位"] : ["距離合う"]) : [],
    };

    if (!partial.name) {
      partial.name = sport.id === "kyotei" ? BOAT_RACERS[(num + 5) % BOAT_RACERS.length] : `馬名${num}`;
    }

    competitors.push(
      sport.id === "kyotei" 
        ? buildKyoteiCompetitor(num, total, partial, 2.0 + num)
        : buildKeibaCompetitor(num, total, partial, 5.0 + num)
    );
  }

  return {
    ...card,
    competitors,
  };
}
