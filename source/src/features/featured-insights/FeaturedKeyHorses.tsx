import Link from "next/link";
import { Card } from "@/components/Card";
import type { KeyCompetitor } from "@/types/race";
import { getActiveSport } from "@/core/sport";
import type { UiState } from "@/types/user";
import { LockedPlaceholder } from "./LockedPlaceholder";

const sport = getActiveSport();

interface Props {
  /** null の場合は未取得（権限なし）→ マスク UI を表示 */
  items: KeyCompetitor[] | null;
  uiState: UiState;
  /** true のとき: ブラー + メッセージを表示しつつ、下部に実データ1行のみピーク表示 */
  locked?: boolean;
}

export function FeaturedKeyHorses({ items, uiState, locked }: Props) {
  return (
    <Card className="p-0">
      <div className="p-4 sm:p-6">
        <h2 className="text-lg font-bold text-gray-900">
          {sport.labels.featuredKeyTitle}
        </h2>
      </div>

      {locked ? (
        /* ロック状態: ぼかし + 中央メッセージ。下部に実データ1行のみ見せて課金を訴求 */
        <>
          <div className="px-4 pb-2 sm:px-6">
            <LockedPlaceholder
              uiState={uiState}
              variant="row"
              rows={4}
              message="プロプラン以上で表示されます"
            />
          </div>
          {items && items.length > 0 ? (
            <ul className="divide-y divide-gray-100 border-t border-gray-100">
              {items.map((h) => (
                <ItemRow key={`${h.rank}-${h.name}`} h={h} />
              ))}
            </ul>
          ) : null}
        </>
      ) : items && items.length > 0 ? (
        /* 解放状態: 全件表示 */
        <ul className="divide-y divide-gray-100">
          {items.map((h) => (
            <ItemRow key={`${h.rank}-${h.name}`} h={h} />
          ))}
        </ul>
      ) : null}
    </Card>
  );
}

function ItemRow({ h }: { h: KeyCompetitor }) {
  return (
    <li>
      <Link
        href={`/race/${h.eventId}`}
        className="flex items-center gap-4 px-4 py-4 text-sm transition hover:bg-gray-50 sm:px-6"
        data-testid={`featured-key-horse-${h.rank}`}
      >
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-50 text-sm font-bold text-blue-600">
          {h.rank}
        </span>

        <div className="flex flex-1 flex-col gap-2 sm:grid sm:grid-cols-12 sm:items-center sm:gap-4">
          <span className="font-bold text-gray-900 sm:col-span-3">{h.name}</span>
          <span className="text-gray-600 sm:col-span-2">
            {h.venue}{h.eventNumber}{sport.labels.eventNumberSuffix}
          </span>
          <span className="text-gray-600 sm:col-span-2">
            {sport.labels.winRate}{" "}
            <span className="font-bold text-blue-600">{Math.round(h.winRate)}%</span>
          </span>
          <span className="text-gray-600 sm:col-span-2">
            {sport.labels.expectedValue}{" "}
            <span className={`font-bold ${h.expectedValue >= 10 ? "text-emerald-600" : "text-gray-500"}`}>
              +{h.expectedValue.toFixed(1)}%
            </span>
          </span>
          <span className="hidden truncate text-gray-500 sm:col-span-3 md:block">
            {h.comment}
          </span>
        </div>

        <span aria-hidden className="shrink-0 text-gray-400">›</span>
      </Link>
    </li>
  );
}
