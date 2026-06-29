"use client";

import { useTransition, useState, useEffect, useRef } from "react";
import { useRouter, useSearchParams, usePathname } from "next/navigation";
import { formatJpDate } from "@/lib/date";

interface Props {
  /** 表示中の日付 (YYYY-MM-DD)。サーバーで決定された値を渡す */
  value: string;
  /** 実データが投入されている開催日の一覧 (新しい順)。クイック選択やカレンダーの「開催日」判定に使用 */
  availableDates?: string[];
  /** 将来: ピッカー等を開くトリガー。未指定ならネイティブの代わりにカスタムカレンダーピッカーを利用 */
  onOpenPicker?: () => void;
}

/**
 * トップページ用の日付選択欄。
 * 添付画像のようなカスタムカレンダーピッカーを内蔵し、開催日と選択日を視覚的に表示します。
 */
export function DateSelector({
  value,
  availableDates,
  onOpenPicker,
}: Props) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();

  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // カレンダーの表示月管理
  const [viewYear, setViewYear] = useState<number>(() => {
    const [y] = value.split("-").map(Number);
    return y || new Date().getFullYear();
  });
  const [viewMonth, setViewMonth] = useState<number>(() => {
    const [, m] = value.split("-").map(Number);
    return m ? m - 1 : new Date().getMonth();
  });

  // 選択日が変わったら表示月を合わせる
  useEffect(() => {
    const [y, m] = value.split("-").map(Number);
    if (y && m) {
      setViewYear(y);
      setViewMonth(m - 1);
    }
  }, [value]);

  // カレンダー外クリックで閉じる
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  function navigateTo(next: string) {
    const params = new URLSearchParams(searchParams?.toString() ?? "");
    params.set("date", next);
    // 強制的にキャッシュをバイパスするためのタイムスタンプを付与
    params.set("t", Date.now().toString());
    const url = `${pathname}?${params.toString()}`;
    startTransition(() => {
      router.push(url);
    });
  }

  // カレンダーの月移動
  const handlePrevMonth = () => {
    if (viewMonth === 0) {
      setViewYear((y) => y - 1);
      setViewMonth(11);
    } else {
      setViewMonth((m) => m - 1);
    }
  };

  const handleNextMonth = () => {
    if (viewMonth === 11) {
      setViewYear((y) => y + 1);
      setViewMonth(0);
    } else {
      setViewMonth((m) => m + 1);
    }
  };

  // カレンダーグリッド用セル生成
  const firstDayIndex = new Date(viewYear, viewMonth, 1).getDay();
  const totalDays = new Date(viewYear, viewMonth + 1, 0).getDate();

  const cells: (number | null)[] = [];
  for (let i = 0; i < firstDayIndex; i++) {
    cells.push(null);
  }
  for (let day = 1; day <= totalDays; day++) {
    cells.push(day);
  }

  const yearStr = String(viewYear);
  const monthStr = String(viewMonth + 1).padStart(2, "0");

  return (
    <div
      className="inline-flex flex-wrap items-center gap-4"
      data-testid="date-selector-root"
      ref={containerRef}
    >
      <div className="relative">
        <button
          type="button"
          onClick={() => {
            if (onOpenPicker) {
              onOpenPicker();
            } else {
              setIsOpen(!isOpen);
            }
          }}
          className="inline-flex items-center gap-2 rounded-xl border border-gray-200 bg-white px-4 py-2.5 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 font-medium text-lg text-gray-900 transition-colors"
          data-testid="date-selector-trigger"
        >
          <CalendarIcon className="h-5 w-5 text-gray-600" />
          <span
            className="font-semibold"
            data-testid="date-selector-label"
          >
            {formatJpDate(value)}
          </span>
        </button>

        {isOpen && (
          <div className="absolute left-0 mt-2 z-50 w-[320px] rounded-xl border border-gray-200 bg-white p-4 shadow-lg">
            {/* カレンダーヘッダー */}
            <div className="flex items-center justify-between mb-4 px-1">
              <button
                type="button"
                onClick={handlePrevMonth}
                className="flex h-8 w-8 items-center justify-center rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 hover:text-gray-900 transition-colors"
                aria-label="前月"
              >
                <ChevronLeftIcon className="h-4 w-4" />
              </button>
              <span className="text-sm font-bold text-gray-800">
                {viewYear}年 {viewMonth + 1}月
              </span>
              <button
                type="button"
                onClick={handleNextMonth}
                className="flex h-8 w-8 items-center justify-center rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 hover:text-gray-900 transition-colors"
                aria-label="次月"
              >
                <ChevronRightIcon className="h-4 w-4" />
              </button>
            </div>

            {/* 曜日ヘッダー */}
            <div className="grid grid-cols-7 gap-y-1 text-center mb-2">
              {["日", "月", "火", "水", "木", "金", "土"].map((d) => (
                <span key={d} className="text-xs font-semibold text-gray-500 py-1">
                  {d}
                </span>
              ))}
            </div>

            {/* 日グリッド */}
            <div className="grid grid-cols-7 gap-1.5 justify-items-center">
              {cells.map((day, idx) => {
                if (day === null) {
                  return <div key={`empty-${idx}`} className="w-9 h-9" />;
                }
                const dayStr = String(day).padStart(2, "0");
                const dateStr = `${yearStr}-${monthStr}-${dayStr}`;
                const isSelected = dateStr === value;
                
                // 過去のデータがあるか（DB依存）、または未来の中央競馬（土日）か
                const dateObj = new Date(viewYear, viewMonth, day);
                const isFuture = dateObj.getTime() > new Date().getTime();
                const isWeekend = dateObj.getDay() === 0 || dateObj.getDay() === 6; // 0:日, 6:土
                const isAvailable = availableDates?.includes(dateStr) || (isFuture && isWeekend);

                const hasAvailableDates = availableDates && availableDates.length > 0;
                // データが空の場合の安全弁、または有効な開催予定日
                const isSelectable = !hasAvailableDates || isAvailable;

                return (
                  <button
                    key={day}
                    type="button"
                    disabled={!isSelectable}
                    onClick={() => {
                      navigateTo(dateStr);
                      setIsOpen(false);
                    }}
                    className={`w-9 h-9 flex items-center justify-center rounded-lg text-sm font-semibold transition-all ${
                      isSelected
                        ? "bg-blue-600 text-white font-bold shadow-sm"
                        : isAvailable
                          ? "bg-blue-50 text-blue-600 border border-blue-100/30 hover:bg-blue-100"
                          : !hasAvailableDates
                            ? "text-gray-700 hover:bg-gray-100"
                            : "text-gray-300 cursor-not-allowed"
                    }`}
                  >
                    {day}
                  </button>
                );
              })}
            </div>

            {/* 凡例 (Legend) */}
            <div className="border-t border-gray-100 pt-3 mt-4 flex items-center justify-start gap-6 text-[11px] text-gray-500 font-medium px-1">
              <div className="flex items-center gap-1.5">
                <span className="w-3.5 h-3.5 rounded bg-blue-50 border border-blue-100/50" />
                <span>開催日</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-3.5 h-3.5 rounded bg-blue-600 shadow-sm" />
                <span>選択日</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {isPending && (
        <span className="text-xs text-gray-400 animate-pulse">読み込み中…</span>
      )}
    </div>
  );
}

function CalendarIcon({ className = "" }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      aria-hidden
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
      />
    </svg>
  );
}

function ChevronDownIcon({ className = "" }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      aria-hidden
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M19 9l-7 7-7-7"
      />
    </svg>
  );
}

function ChevronLeftIcon({ className = "" }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      aria-hidden
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M15 19l-7-7 7-7"
      />
    </svg>
  );
}

function ChevronRightIcon({ className = "" }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      aria-hidden
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M9 5l7 7-7 7"
      />
    </svg>
  );
}
