"use client";

import { useRouter } from "next/navigation";
import type { UiState } from "@/types/user";

interface Props {
  uiState: UiState;
  trialDaysLeft?: number | null;
}

export function UpgradeCta({ uiState, trialDaysLeft }: Props) {
  const router = useRouter();

  if (uiState === "trial" && trialDaysLeft != null) {
    return (
      <div className="rounded-lg bg-blue-50 px-4 py-2 text-center text-sm text-blue-700">
        無料トライアル残り <strong>{trialDaysLeft}日</strong> —{" "}
        <button
          className="underline hover:text-blue-900"
          onClick={() => router.push("/pricing")}
        >
          プロプランを見る
        </button>
      </div>
    );
  }

  if (uiState === "expired") {
    return (
      <div className="rounded-lg bg-amber-50 px-4 py-2 text-center text-sm text-amber-700">
        トライアル期間が終了しました。AI予想をすべて見るには{" "}
        <button
          className="font-medium underline hover:text-amber-900"
          onClick={() => router.push("/pricing")}
          data-testid="expired-upgrade-cta"
        >
          プロ登録
        </button>{" "}
        してください。
      </div>
    );
  }

  return null;
}
