"use client";

import { useMemo } from "react";
import { useRouter } from "next/navigation";
import type { EventSummary } from "@/types/race";
import type { UiState } from "@/types/user";
import type { GatingPolicy } from "@/features/plan-gating/policy";
import { RaceCard } from "./RaceCard";
import { UpgradeCta } from "@/features/plan-gating/UpgradeCta";

const VENUE_ORDER = [
  // 競馬
  "中山", "阪神", "中京", "東京", "京都", "福島", "新潟", "小倉", "札幌", "函館",
  // 競艇
  "桐生", "戸田", "江戸川", "平和島", "多摩川", "浜名湖", "蒲郡", "常滑", "津",
  "三国", "びわこ", "住之江", "尼崎", "鳴門", "丸亀", "児島", "宮島", "徳山",
  "下関", "若松", "芦屋", "福岡", "佐賀", "大村"
];

interface Props {
  races: EventSummary[];
  uiState: UiState;
  policy: GatingPolicy;
}

function sortVenues(venues: string[]): string[] {
  return [...venues].sort((a, b) => {
    const idxA = VENUE_ORDER.indexOf(a);
    const idxB = VENUE_ORDER.indexOf(b);
    if (idxA !== -1 && idxB !== -1) return idxA - idxB;
    if (idxA !== -1) return -1;
    if (idxB !== -1) return 1;
    return a.localeCompare(b, "ja");
  });
}

export function RaceListClient({ races, uiState, policy }: Props) {
  const router = useRouter();

  function handleLockedClick() {
    if (policy.showLoginCta) {
      router.push("/login?returnTo=/");
    } else {
      router.push("/pricing");
    }
  }

  const { venues, raceNumbers, raceLookup } = useMemo(() => {
    const byVenue = new Map<string, EventSummary[]>();
    for (const race of races) {
      const list = byVenue.get(race.venue) ?? [];
      list.push(race);
      byVenue.set(race.venue, list);
    }
    for (const list of byVenue.values()) {
      list.sort((a, b) => a.eventNumber - b.eventNumber);
    }

    const venues = sortVenues(Array.from(byVenue.keys()));
    const raceNumbers = Array.from(
      new Set(races.map((r) => r.eventNumber)),
    ).sort((a, b) => a - b);

    const raceLookup = new Map<string, EventSummary>();
    for (const race of races) {
      raceLookup.set(`${race.venue}-${race.eventNumber}`, race);
    }

    return { venues, raceNumbers, raceLookup };
  }, [races]);

  // 会場数だけ列を作り、同じ R の行を全会場で横並びに揃える。
  // Tailwind の grid-cols-N は会場数が可変だと表現しきれないため inline style で指定する。
  const gridStyle = {
    gridTemplateColumns: `repeat(${Math.max(venues.length, 1)}, minmax(0, 1fr))`,
  };

  return (
    <div className="space-y-4">
      <UpgradeCta uiState={uiState} trialDaysLeft={policy.trialDaysLeft} />

      {races.length === 0 ? (
        <p className="py-12 text-center text-sm text-gray-400">
          レースデータがありません
        </p>
      ) : (
        <div className="-mx-4 overflow-x-auto sm:mx-0">
          <div className="min-w-[800px] space-y-2 px-4 sm:min-w-0 sm:space-y-3 sm:px-0">
            {/* 会場ヘッダー */}
            <div className="grid gap-2 sm:gap-3" style={gridStyle}>
              {venues.map((venue) => (
                <div
                  key={venue}
                  className="rounded-lg border border-gray-200 bg-gray-50 py-2 text-center text-sm font-bold text-gray-900"
                >
                  {venue}
                </div>
              ))}
            </div>

            {/* レース番号ごとの行（1R・2R…を横並びで一括比較） */}
            {raceNumbers.map((raceNo) => (
              <div
                key={raceNo}
                className="grid gap-2 sm:gap-3"
                style={gridStyle}
              >
                {venues.map((venue) => {
                  const race = raceLookup.get(`${venue}-${raceNo}`);
                  if (!race) {
                    return (
                      <div
                        key={`${venue}-${raceNo}-empty`}
                        className="min-h-[9rem] rounded-lg border border-dashed border-gray-100 bg-gray-50/40"
                        aria-hidden
                      />
                    );
                  }
                  return (
                    <RaceCard
                      key={race.id}
                      race={race}
                      policy={policy}
                      onLockedClick={handleLockedClick}
                      compact
                    />
                  );
                })}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
