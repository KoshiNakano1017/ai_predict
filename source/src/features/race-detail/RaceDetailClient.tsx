"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import type { RaceEvent } from "@/types/race";
import type { GatingPolicy } from "@/features/plan-gating/policy";
import type { UiState } from "@/types/user";
import { AiPredictionSection } from "./AiPredictionSection";
import { EntriesTable } from "./EntriesTable";

interface Props {
  race: RaceEvent;
  policy: GatingPolicy;
  uiState: UiState;
}

/** 未ログインユーザー向け CTA セクション（Figma D-3） */
function GuestCtaSection() {
  return (
    <div className="rounded-2xl bg-blue-50 p-6 sm:p-8">
      <div className="flex flex-col items-center gap-4 text-center">
        <svg
          className="h-10 w-10 text-blue-500"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          aria-hidden
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
          />
        </svg>

        <h3 className="text-lg font-bold text-gray-900">
          ログインすると以下が解放されます
        </h3>

        <ul className="space-y-1 text-sm text-gray-600">
          <li className="flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-blue-500" />
            全馬の勝率 / 期待値
          </li>
          <li className="flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-blue-500" />
            高期待値ランキング
          </li>
          <li className="flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-blue-500" />
            詳細分析
          </li>
        </ul>

        <div className="flex flex-wrap justify-center gap-3 pt-1">
          <Link href="/signup">
            <button
              type="button"
              className="rounded-lg bg-blue-600 px-6 py-2.5 text-sm font-bold text-white transition hover:bg-blue-700"
            >
              無料で始める
            </button>
          </Link>
          <Link href="/login">
            <button
              type="button"
              className="rounded-lg border border-gray-300 bg-white px-6 py-2.5 text-sm font-bold text-gray-700 transition hover:bg-gray-50"
            >
              ログイン
            </button>
          </Link>
        </div>
      </div>
    </div>
  );
}

export function RaceDetailClient({ race, policy, uiState }: Props) {
  const router = useRouter();

  function handleLockedClick() {
    if (policy.showLoginCta) {
      router.push(`/login?returnTo=/race/${race.id}`);
    } else {
      router.push("/pricing");
    }
  }

  return (
    <div className="space-y-6">
      <AiPredictionSection
        race={race}
        policy={policy}
        onLockedClick={handleLockedClick}
      />
      {uiState === "guest" && <GuestCtaSection />}
      <EntriesTable entries={race.competitors} policy={policy} />
    </div>
  );
}
