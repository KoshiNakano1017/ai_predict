"use client";

import Link from "next/link";
import type { EventSummary } from "@/types/race";
import { getActiveSport } from "@/core/sport";
import type { GatingPolicy } from "@/features/plan-gating/policy";

const sport = getActiveSport();

interface Props {
  race: EventSummary;
  policy: GatingPolicy;
  onLockedClick: () => void;
  /** 3列グリッド用のコンパクト表示 */
  compact?: boolean;
}

function formatRate(value: number): string {
  return `${Math.round(value)}%`;
}

function formatEv(value: number): string {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(1)}%`;
}

function PickCell({
  icon,
  label,
  name,
  winRate,
  expectedValue,
  nameClassName,
  compact,
  canViewValues,
}: {
  icon: string;
  label: string;
  name: string | null;
  winRate?: number | null;
  expectedValue?: number | null;
  nameClassName?: string;
  compact?: boolean;
  canViewValues: boolean;
}) {
  const evClass =
    canViewValues && expectedValue != null && expectedValue >= 10
      ? "text-emerald-600 font-bold"
      : "text-gray-400";

  return (
    <div className={compact ? "min-w-0" : ""}>
      <div
        className={
          compact
            ? "mb-0.5 text-[10px] font-medium leading-tight text-gray-500"
            : "mb-1 text-xs font-bold text-gray-500"
        }
      >
        <span className="text-gray-700">{icon}</span> {label}
      </div>
      {!canViewValues ? (
        /* 未ログイン: 馬名・勝率・期待値すべてマスク */
        <div className="space-y-0">
          <div className={`font-bold tracking-widest text-gray-300 ${compact ? "text-[11px] leading-tight" : ""}`}>
            ★★★
          </div>
          {winRate != null && (
            <div className={compact ? "text-[10px] leading-tight text-gray-400" : "text-xs text-gray-400"}>
              {sport.labels.winRate}：??%
            </div>
          )}
          {expectedValue != null && (
            <div className={compact ? "text-[10px] leading-tight text-gray-400" : "text-xs text-gray-400"}>
              {sport.labels.expectedValue}：+??%
            </div>
          )}
        </div>
      ) : name ? (
        <div className="space-y-0">
          <div
            className={`truncate font-bold text-gray-900 ${compact ? "text-[11px] leading-tight" : ""} ${nameClassName ?? ""}`}
            title={name}
          >
            {name}
          </div>
          {winRate != null && (
            <div className={compact ? "text-[10px] leading-tight text-blue-600 font-bold" : "text-xs text-blue-600 font-bold"}>
              {sport.labels.winRate}：{formatRate(winRate)}
            </div>
          )}
          {expectedValue != null && (
            <div className={compact ? `text-[10px] leading-tight ${evClass}` : `text-xs ${evClass}`}>
              {sport.labels.expectedValue}：{formatEv(expectedValue)}
            </div>
          )}
        </div>
      ) : (
        <div className={compact ? "text-[10px] text-gray-400" : "text-gray-400"}>
          なし
        </div>
      )}
    </div>
  );
}

/** ⚠◆ のロック時プレースホルダー（★★★テキストのみ、ボタンなし） */
function LockedPickCell({
  icon,
  label,
  compact,
}: {
  icon: string;
  label: string;
  compact?: boolean;
}) {
  return (
    <div className={compact ? "min-w-0" : ""}>
      <div
        className={
          compact
            ? "mb-0.5 text-[10px] font-medium leading-tight text-gray-500"
            : "mb-1 text-xs font-bold text-gray-500"
        }
      >
        <span className="text-gray-700">{icon}</span> {label}
      </div>
      <div className={compact ? "text-[10px] tracking-widest text-gray-300" : "text-sm tracking-widest text-gray-300"}>
        ★★★
      </div>
    </div>
  );
}

export function RaceCard({ race, policy, onLockedClick: _onLockedClick, compact }: Props) {
  const maxEv = Math.max(
    race.topPicks.star?.expectedValue ?? 0,
    race.topPicks.triangle?.expectedValue ?? 0,
  );
  const isRecommended = maxEv >= 10;

  const padding = compact ? "p-2 sm:p-2.5" : "p-4";
  const headerText = compact
    ? "text-[10px] font-medium leading-tight text-gray-700"
    : "text-sm font-medium text-gray-700";
  const badgeText = compact
    ? "rounded px-1 py-px text-[9px] font-bold leading-none"
    : "rounded px-2 py-0.5 text-xs font-bold";
  const gridGap = compact ? "gap-1.5" : "gap-4";
  const sectionPt = compact ? "pt-1.5" : "pt-4";
  const headerMb = compact ? "mb-1.5" : "mb-4";

  return (
    <Link
      href={`/race/${race.id}`}
      data-testid={`race-card-${race.id}`}
      className={`block h-full rounded-lg border border-gray-200 bg-white transition hover:bg-gray-50 active:bg-gray-100 ${compact ? "shadow-sm" : ""}`}
    >
      <div className={padding}>
        <div className={`flex items-start justify-between gap-1 ${headerMb}`}>
          <div className={`min-w-0 flex-1 ${headerText}`}>
            <span className="font-semibold">{race.eventNumber}{sport.labels.eventNumberSuffix}</span>{" "}
            {sport.formatConditions(race.conditions)}{" "}
            <span className={compact ? "ml-0.5" : "ml-1"}>{race.title}</span>
          </div>
          <div
            className={`shrink-0 ${badgeText} ${
              isRecommended
                ? "bg-yellow-100 text-yellow-800"
                : "bg-gray-100 text-gray-600"
            }`}
          >
            {isRecommended ? sport.labels.recommended : sport.labels.notRecommended}
          </div>
        </div>

        {/* ★ ▲ 行 */}
        <div className={`grid grid-cols-2 ${gridGap} border-t border-gray-100 ${sectionPt} ${compact ? "text-[10px]" : "text-sm"}`}>
          <PickCell
            icon={sport.ratings.star.icon}
            label={sport.ratings.star.label}
            name={race.topPicks.star?.name ?? null}
            winRate={race.topPicks.star?.winRate}
            expectedValue={race.topPicks.star?.expectedValue}
            compact={compact}
            canViewValues={policy.canViewPredictionValues}
          />
          <PickCell
            icon={sport.ratings.triangle.icon}
            label={sport.ratings.triangle.label}
            name={race.topPicks.triangle?.name ?? null}
            winRate={race.topPicks.triangle?.winRate}
            expectedValue={race.topPicks.triangle?.expectedValue}
            compact={compact}
            canViewValues={policy.canViewPredictionValues}
          />
        </div>

        {/* ⚠ ◆ 行 */}
        <div className={`mt-1.5 grid grid-cols-2 ${gridGap} border-t border-gray-100 ${sectionPt} ${compact ? "text-[10px]" : "text-sm"}`}>
          {policy.canViewCaution ? (
            <PickCell
              icon={sport.ratings.caution.icon}
              label={sport.ratings.caution.label}
              name={race.topPicks.caution?.name ?? null}
              compact={compact}
              canViewValues={true}
            />
          ) : (
            <LockedPickCell
              icon={sport.ratings.caution.icon}
              label={sport.ratings.caution.label}
              compact={compact}
            />
          )}

          {policy.canViewDarkHorse ? (
            <PickCell
              icon={sport.ratings.darkHorse.icon}
              label={sport.ratings.darkHorse.label}
              name={race.topPicks.darkHorse?.name ?? null}
              compact={compact}
              canViewValues={true}
              nameClassName="text-emerald-600"
            />
          ) : (
            <LockedPickCell
              icon={sport.ratings.darkHorse.icon}
              label={sport.ratings.darkHorse.label}
              compact={compact}
            />
          )}
        </div>
      </div>
    </Link>
  );
}
