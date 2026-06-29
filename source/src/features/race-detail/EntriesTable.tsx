"use client";

import { useMemo, useState } from "react";
import { Card } from "@/components/Card";
import type { Competitor } from "@/types/race";
import { getActiveSport } from "@/core/sport";
import type { GatingPolicy } from "@/features/plan-gating/policy";

interface Props {
  entries: Competitor[];
  policy: GatingPolicy;
}

const sport = getActiveSport();

type SortKey = "frame" | "number" | "winRate" | "ev";

const SORT_ACCESSORS: Record<SortKey, (e: Competitor) => number | null> = {
  frame: (e) => e.lane,
  number: (e) => e.bib,
  winRate: (e) => e.winRate,
  ev: (e) => e.expectedValue,
};

function formatRate(value: number): string {
  return `${Math.round(value)}%`;
}

function formatEv(value: number): string {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(1)}%`;
}

function SortIcon({ active, dir }: { active: boolean; dir: 1 | -1 }) {
  return (
    <svg
      className={`h-3.5 w-3.5 shrink-0 ${active ? "text-gray-700" : "text-gray-400"}`}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      aria-hidden
    >
      {!active || dir === 1 ? (
        <path strokeLinecap="round" strokeLinejoin="round" d="M8 9l4-4 4 4" />
      ) : null}
      {!active || dir === -1 ? (
        <path strokeLinecap="round" strokeLinejoin="round" d="M8 15l4 4 4-4" />
      ) : null}
    </svg>
  );
}

/** ロック時は実値を渡さず固定ダミーをぼかして表示する */
function MaskedValue() {
  return (
    <span aria-hidden className="select-none text-gray-400 blur-[3px]">
      25%
    </span>
  );
}

export function EntriesTable({ entries, policy }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>("number");
  const [sortDir, setSortDir] = useState<1 | -1>(1);

  const canViewValues = policy.canViewPredictionValues;

  function toggleSort(key: SortKey) {
    if (key === sortKey) {
      setSortDir((d) => (d === 1 ? -1 : 1));
    } else {
      setSortKey(key);
      // 勝率・期待値は「高い順」で見たいのが自然なため降順から始める
      setSortDir(key === "winRate" || key === "ev" ? -1 : 1);
    }
  }

  const sorted = useMemo(() => {
    const accessor = SORT_ACCESSORS[sortKey];
    return [...entries].sort((a, b) => {
      const va = accessor(a);
      const vb = accessor(b);
      if (va == null && vb == null) return a.bib - b.bib;
      if (va == null) return 1;
      if (vb == null) return -1;
      return (va - vb) * sortDir;
    });
  }, [entries, sortKey, sortDir]);

  function SortableTh({
    label,
    sortAs,
    align = "left",
  }: {
    label: string;
    sortAs?: SortKey;
    align?: "left" | "right";
  }) {
    const alignClass = align === "right" ? "text-right" : "text-left";
    if (!sortAs) {
      return (
        <th
          className={`whitespace-nowrap px-3 py-3 font-medium text-gray-500 sm:px-4 ${alignClass}`}
        >
          {label}
        </th>
      );
    }
    return (
      <th
        className={`whitespace-nowrap px-3 py-3 font-medium text-gray-500 sm:px-4 ${alignClass}`}
        aria-sort={
          sortKey === sortAs ? (sortDir === 1 ? "ascending" : "descending") : undefined
        }
      >
        <button
          type="button"
          onClick={() => toggleSort(sortAs)}
          className={`inline-flex items-center gap-0.5 hover:text-gray-700 ${align === "right" ? "flex-row-reverse" : ""}`}
        >
          {label}
          <SortIcon active={sortKey === sortAs} dir={sortDir} />
        </button>
      </th>
    );
  }

  return (
    <Card className="p-0">
      <div className="p-4 sm:p-6">
        <h2 className="text-lg font-bold text-gray-900">{sport.labels.entriesTitle}</h2>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="border-y border-gray-200 bg-gray-50">
            <tr>
              <SortableTh label={sport.labels.lane} sortAs="frame" />
              <SortableTh label={sport.labels.bib} sortAs="number" />
              <SortableTh label={sport.labels.competitor} />
              <SortableTh label={sport.labels.winRate} sortAs="winRate" align="right" />
              <SortableTh label={sport.labels.expectedValue} sortAs="ev" align="right" />
              <SortableTh label={sport.labels.reason} />
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {sorted.map((entry) => (
              <tr key={entry.bib} className="hover:bg-gray-50">
                <td className="px-3 py-4 tabular-nums text-gray-700 sm:px-4">
                  {entry.lane ?? "—"}
                </td>
                <td className="px-3 py-4 tabular-nums text-gray-700 sm:px-4">
                  {entry.bib}
                </td>
                <td className="px-3 py-4 sm:px-4">
                  <span className="break-anywhere font-bold text-gray-900">
                    {entry.name}
                  </span>
                </td>
                <td className="whitespace-nowrap px-3 py-4 text-right tabular-nums sm:px-4">
                  {!canViewValues ? (
                    <MaskedValue />
                  ) : entry.winRate != null ? (
                    <span className="font-bold text-blue-600">
                      {formatRate(entry.winRate)}
                    </span>
                  ) : (
                    <span className="text-gray-400">—</span>
                  )}
                </td>
                <td className="whitespace-nowrap px-3 py-4 text-right tabular-nums sm:px-4">
                  {!canViewValues ? (
                    <MaskedValue />
                  ) : entry.expectedValue != null ? (
                    <span
                      className={
                        entry.expectedValue >= 10
                          ? "font-bold text-emerald-600"
                          : "text-gray-500"
                      }
                    >
                      {formatEv(entry.expectedValue)}
                    </span>
                  ) : (
                    <span className="text-gray-400">—</span>
                  )}
                </td>
                <td className="min-w-[16rem] max-w-md px-3 py-4 text-gray-600 sm:px-4">
                  {entry.reason ?? "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
