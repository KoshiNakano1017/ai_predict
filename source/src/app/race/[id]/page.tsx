import type { Metadata } from "next";
import Link from "next/link";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { Card } from "@/components/Card";
import { Button } from "@/components/Button";
import { RaceDetailClient } from "@/features/race-detail/RaceDetailClient";
import { createRaceRepository } from "@/lib/repositories/race";
import { createUserRepository } from "@/lib/repositories/user";
import { deriveUiState } from "@/types/user";
import { derivePolicy } from "@/features/plan-gating/policy";
import { getActiveSport } from "@/core/sport";
import { notFound } from "next/navigation";

const sport = getActiveSport();

export const metadata: Metadata = { title: `${getActiveSport().labels.event}詳細 | ${getActiveSport().labels.serviceName}` };

interface Props {
  params: Promise<{ id: string }>;
}

export default async function RaceDetailPage({ params }: Props) {
  const { id } = await params;
  const [race, user] = await Promise.all([
    createRaceRepository().getRaceDetail(id),
    createUserRepository().getCurrentUser(),
  ]);

  if (!race) notFound();

  const uiState = deriveUiState(user);
  const policy = derivePolicy(uiState, user?.trialEndsAt ?? null);

  // 一覧カードと同じ基準: ★/▲ の期待値が 10% 以上なら「注目」
  const maxEv = Math.max(
    ...race.competitors
      .filter((e) => e.rating === "★" || e.rating === "▲")
      .map((e) => e.expectedValue ?? 0),
    0,
  );
  const isRecommended = maxEv >= 10;

  return (
    <>
      <Header uiState={uiState} userRole={user?.role} />
      <main className="mx-auto max-w-5xl space-y-6 px-4 py-6">
        <Link
          href="/"
          className="inline-flex min-h-[44px] items-center gap-1 text-sm text-gray-500 hover:text-gray-700"
        >
          ← {sport.labels.event}一覧に戻る
        </Link>

        {/* レース基本情報 */}
        <Card className="p-4 sm:p-6">
          <p className="text-sm text-gray-500">
            {race.venue}　{race.eventNumber}{sport.labels.eventNumberSuffix}　{sport.formatConditions(race.conditions)}
          </p>
          <h1 className="mt-2 break-anywhere text-2xl font-bold text-gray-900 sm:text-3xl">
            {race.title}
          </h1>
          <div className="mt-4 flex items-center gap-2 text-sm text-gray-500">
            {sport.labels.event}評価：
            <span
              className={`rounded px-2 py-0.5 text-xs font-bold ${
                isRecommended
                  ? "bg-yellow-100 text-yellow-800"
                  : "bg-gray-100 text-gray-600"
              }`}
            >
              {isRecommended ? sport.labels.recommended : sport.labels.notRecommended}
            </span>
          </div>
        </Card>

        {/* AI予想 + GuestCTA（未ログイン時） + 全出走馬の詳細データ */}
        <RaceDetailClient race={race} policy={policy} uiState={uiState} />

        {/* トライアル期限切れ向けアップグレード CTA */}
        {policy.showUpgradeCta && (
          <div className="rounded-lg bg-gray-50 p-6 text-center">
            <p className="mb-3 text-sm text-gray-600">
              トライアル期間終了後もAI予想をご利用いただくにはプロ登録が必要です
            </p>
            <Link href="/pricing">
              <Button data-testid="race-detail-cta">プロ登録</Button>
            </Link>
          </div>
        )}
      </main>
      <Footer />
    </>
  );
}
