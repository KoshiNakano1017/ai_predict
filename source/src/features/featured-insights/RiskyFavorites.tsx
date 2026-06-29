import Link from "next/link";
import { Card } from "@/components/Card";
import type { RiskyFavorite } from "@/types/race";
import { getActiveSport } from "@/core/sport";
import type { UiState } from "@/types/user";
import { LockedPlaceholder } from "./LockedPlaceholder";

const sport = getActiveSport();

interface Props {
  items: RiskyFavorite[] | null;
  uiState: UiState;
  locked?: boolean;
}

export function RiskyFavorites({ items, uiState, locked }: Props) {
  return (
    <Card className="p-4 sm:p-6">
      <h2 className="mb-4 flex items-center gap-2 text-base font-bold text-gray-900">
        <svg className="h-5 w-5 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        {sport.labels.riskyTitle}
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

function ItemRow({ h, i }: { h: RiskyFavorite; i: number }) {
  return (
    <li>
      <Link
        href={`/race/${h.eventId}`}
        data-testid={`risky-favorite-${i}`}
        className="grid grid-cols-[auto_3.5rem_1fr] items-center gap-2 py-3 text-sm transition hover:bg-gray-50 sm:gap-3 md:grid-cols-[auto_3.5rem_1fr_auto]"
      >
        <svg className="h-4 w-4 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        <span className="text-gray-500">{h.venue}{h.eventNumber}{sport.labels.eventNumberSuffix}</span>
        <span className="truncate font-bold text-gray-700">{h.name}</span>
        <span className="hidden truncate text-right text-gray-500 md:block">{h.reason}</span>
      </Link>
    </li>
  );
}
