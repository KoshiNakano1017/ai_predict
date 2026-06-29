import Link from "next/link";
import { Card } from "@/components/Card";
import type { Longshot } from "@/types/race";
import { getActiveSport } from "@/core/sport";
import type { UiState } from "@/types/user";
import { LockedPlaceholder } from "./LockedPlaceholder";

const sport = getActiveSport();

interface Props {
  items: Longshot[] | null;
  uiState: UiState;
  locked?: boolean;
}

export function LongshotHorses({ items, uiState, locked }: Props) {
  return (
    <Card className="p-4 sm:p-6">
      <h2 className="mb-4 flex items-center gap-2 text-base font-bold text-gray-900">
        <svg className="h-5 w-5 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
        </svg>
        {sport.labels.longshotTitle}
      </h2>

      {locked ? (
        <>
          <LockedPlaceholder
            uiState={uiState}
            variant="list"
            rows={4}
            message="プロプラン以上で全頭のデータが表示されます"
          />
          {items && items.length > 0 ? (
            <ul className="mt-2 divide-y divide-gray-100 border-t border-gray-100">
              {items.map((h, i) => (
                <ItemRow key={`${h.venue}-${h.eventNumber}-${h.name}`} h={h} i={i} />
              ))}
            </ul>
          ) : null}
        </>
      ) : items && items.length > 0 ? (
        <ul className="divide-y divide-gray-100">
          {items.map((h, i) => (
            <ItemRow key={`${h.venue}-${h.eventNumber}-${h.name}`} h={h} i={i} />
          ))}
        </ul>
      ) : null}
    </Card>
  );
}

function ItemRow({ h, i }: { h: Longshot; i: number }) {
  return (
    <li>
      <Link
        href={`/race/${h.eventId}`}
        data-testid={`longshot-horse-${i}`}
        className="grid grid-cols-[auto_3.5rem_1fr_auto] items-center gap-2 py-3 text-sm transition hover:bg-gray-50 sm:gap-3"
      >
        <svg className="h-4 w-4 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
        </svg>
        <span className="text-gray-500">{h.venue}{h.eventNumber}{sport.labels.eventNumberSuffix}</span>
        <span className="truncate font-bold text-gray-700">{h.name}</span>
        <div className="flex items-center justify-end gap-1.5 text-gray-600 sm:gap-2">
          <span>{sport.labels.expectedValue}</span>
          <span className={`w-12 text-right tabular-nums ${h.expectedValue >= 10 ? "text-emerald-600 font-bold" : "text-gray-500"}`}>
            +{h.expectedValue.toFixed(1)}%
          </span>
        </div>
      </Link>
    </li>
  );
}
