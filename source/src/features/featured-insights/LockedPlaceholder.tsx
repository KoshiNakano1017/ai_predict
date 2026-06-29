"use client";

import type { UiState } from "@/types/user";

interface Props {
  uiState: UiState;
  variant?: "row" | "list";
  /** ぼかし表示するダミー行数 */
  rows?: number;
  /** 画面上のメッセージ（UI 仕様準拠） */
  message?: string;
}

/**
 * プラン未該当時のマスク UI。
 *
 * 重要: 本コンポーネントは "表示の目隠し" ではなく
 *   - サーバー側で実データを取得しない（page.tsx で gating）
 *   - クライアントには一切の機密データが渡らない
 * ことを前提とする最終段の視覚装飾である。
 */
export function LockedPlaceholder({
  uiState: _uiState,
  variant = "list",
  rows = 5,
  message = "プロプラン以上で表示されます",
}: Props) {
  return (
    <div className="relative overflow-hidden rounded-lg">
      <div
        className="pointer-events-none select-none space-y-3 p-4 blur-[4px]"
        aria-hidden
      >
        {Array.from({ length: rows }).map((_, i) =>
          variant === "row" ? (
            <DummyRow key={i} />
          ) : (
            <DummyListItem key={i} />
          ),
        )}
      </div>

      <div className="absolute inset-0 flex items-center justify-center bg-gray-500/20 backdrop-blur-[1px]">
        <div className="rounded-2xl bg-white px-6 py-3 shadow-lg">
          <p className="text-sm font-medium text-gray-800">{message}</p>
        </div>
      </div>
    </div>
  );
}

function DummyRow() {
  return (
    <div className="flex items-center gap-3">
      <div className="h-6 w-6 rounded-full bg-gray-200" />
      <div className="h-4 flex-1 rounded bg-gray-200" />
      <div className="h-4 w-16 rounded bg-gray-200" />
      <div className="h-4 w-12 rounded bg-gray-200" />
      <div className="h-4 w-14 rounded bg-gray-200" />
    </div>
  );
}

function DummyListItem() {
  return (
    <div className="flex items-center gap-3">
      <div className="h-4 w-4 rounded bg-gray-200" />
      <div className="h-4 flex-1 rounded bg-gray-200" />
      <div className="h-4 w-16 rounded bg-gray-200" />
    </div>
  );
}
