"use client";

import { Card } from "@/components/Card";
import type { RaceEvent, Competitor } from "@/types/race";
import { getActiveSport } from "@/core/sport";
import type { GatingPolicy } from "@/features/plan-gating/policy";

interface Props {
  race: RaceEvent;
  policy: GatingPolicy;
  onLockedClick: () => void;
}

type PickKind = "star" | "triangle" | "caution" | "darkHorse";

const sport = getActiveSport();

const PICK_STYLE: Record<PickKind, { labelClass: string; chipClass: string }> = {
  star:      { labelClass: "text-gray-600",    chipClass: "bg-blue-50 text-blue-700" },
  triangle:  { labelClass: "text-gray-600",    chipClass: "bg-blue-50 text-blue-700" },
  caution:   { labelClass: "text-red-600",     chipClass: "bg-red-50 text-red-600" },
  darkHorse: { labelClass: "text-emerald-700", chipClass: "bg-emerald-50 text-emerald-700" },
};

const PICK_META: Record<
  PickKind,
  { icon: string; label: string; labelClass: string; chipClass: string }
> = {
  star:      { ...sport.ratings.star,      ...PICK_STYLE.star },
  triangle:  { ...sport.ratings.triangle,  ...PICK_STYLE.triangle },
  caution:   { ...sport.ratings.caution,   ...PICK_STYLE.caution },
  darkHorse: { ...sport.ratings.darkHorse, ...PICK_STYLE.darkHorse },
};

function formatRate(value: number): string {
  return `${Math.round(value)}%`;
}

function formatEv(value: number): string {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(1)}%`;
}

function PickBlock({
  kind,
  entry,
  canViewValues,
}: {
  kind: PickKind;
  entry: Competitor;
  canViewValues: boolean;
}) {
  const meta = PICK_META[kind];
  let evClass = "text-gray-500";
  if (kind === "caution") {
    evClass = "text-red-600";
  } else if (canViewValues && entry.expectedValue != null && entry.expectedValue >= 10) {
    evClass = "text-emerald-600";
  }

  return (
    <div>
      <div className={`mb-2 text-sm font-medium ${meta.labelClass}`}>
        {meta.icon} {meta.label}
      </div>
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between sm:gap-4">
        <div className="min-w-0">
          <div className="break-anywhere text-lg font-bold text-gray-900" title={entry.name}>
            {entry.name}
          </div>
          {entry.tags.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {entry.tags.map((tag) => (
                <span key={tag} className={`rounded px-2 py-0.5 text-xs font-medium ${meta.chipClass}`}>
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>

        <div className="flex shrink-0 items-baseline gap-6 text-sm text-gray-500">
          {entry.winRate != null && (
            <span>
              {sport.labels.winRate}{" "}
              <span className="text-lg font-bold tabular-nums text-blue-600">
                {canViewValues ? formatRate(entry.winRate) : "??%"}
              </span>
            </span>
          )}
          {entry.expectedValue != null && (
            <span>
              {sport.labels.expectedValue}{" "}
              <span className={`text-lg font-bold tabular-nums ${canViewValues ? evClass : "text-gray-400"}`}>
                {canViewValues ? formatEv(entry.expectedValue) : "+??%"}
              </span>
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

/** ⚠◆ のロック時インライン表示（テキストのみ、ボタンなし）*/
function LockedPickBlock({ kind }: { kind: PickKind }) {
  const meta = PICK_META[kind];
  return (
    <div>
      <div className={`mb-2 text-sm font-medium ${meta.labelClass}`}>
        {meta.icon} {meta.label}
      </div>
      <div className="flex items-center gap-3 text-sm text-gray-400">
        <span className="font-bold tracking-widest">★★★</span>
        <span>プロプラン以上でデータが表示されます</span>
      </div>
    </div>
  );
}

export function AiPredictionSection({ race, policy, onLockedClick: _onLockedClick }: Props) {
  const byRating = (rating: Competitor["rating"]) =>
    race.competitors.find((e) => e.rating === rating) ?? null;

  const picks: { kind: PickKind; entry: Competitor | null; locked: boolean }[] = [
    { kind: "star",      entry: byRating("★"), locked: !policy.canViewStar },
    { kind: "triangle",  entry: byRating("▲"), locked: !policy.canViewTriangle },
    { kind: "caution",   entry: byRating("⚠"), locked: !policy.canViewCaution },
    { kind: "darkHorse", entry: byRating("◆"), locked: !policy.canViewDarkHorse },
  ];

  const visible = picks.filter((p) => p.entry != null || p.locked);
  if (visible.length === 0) return null;

  return (
    <Card className="p-4 sm:p-6">
      <h2 className="mb-6 text-lg font-bold text-gray-900">{sport.labels.predictionTitle}</h2>
      <div className="space-y-6 divide-y divide-gray-100 [&>*+*]:pt-6">
        {visible.map(({ kind, entry, locked }) => {
          if (locked) return <LockedPickBlock key={kind} kind={kind} />;
          if (!entry) return null;
          return (
            <PickBlock
              key={kind}
              kind={kind}
              entry={entry}
              canViewValues={policy.canViewPredictionValues}
            />
          );
        })}
      </div>
    </Card>
  );
}
