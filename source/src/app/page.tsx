import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { RaceListClient } from "@/features/race-list/RaceListClient";
import { FeaturedInsightsSection } from "@/features/featured-insights/FeaturedInsightsSection";
import { HeroIntro } from "@/features/hero/HeroIntro";
import { DateSelector } from "@/features/date-selector/DateSelector";
import { createRaceRepository } from "@/lib/repositories/race";
import { createUserRepository } from "@/lib/repositories/user";
import { deriveUiState } from "@/types/user";
import { derivePolicy } from "@/features/plan-gating/policy";
import type { FeaturedInsights } from "@/types/race";

interface Props {
  searchParams: Promise<{ date?: string }>;
}

const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

export const dynamic = 'force-dynamic';
export const revalidate = 0;

export default async function RaceListPage({ searchParams }: Props) {
  // force-dynamic を明示することで静的レンダリング(SSG)時のキャッシュを回避する
  // (searchParams に依存しているため基本的にはDynamic Renderingになるが、念のため)
  const raceRepo = createRaceRepository();
  const sp = await searchParams;

  // 表示対象日の決定:
  // 1. URL クエリ ?date=YYYY-MM-DD があればそれを使う
  // 2. 無ければ Supabase に投入されている最新日 (getLatestRaceDate)
  // 3. それも null なら今日 (フォールバック)
  let targetDate: string | null = null;
  if (sp.date && DATE_RE.test(sp.date)) {
    targetDate = sp.date;
  } else {
    try {
      targetDate = await raceRepo.getLatestRaceDate();
      console.log(`[SSR] targetDate fetched from DB: ${targetDate}`);
    } catch {
      targetDate = null;
    }
  }
  if (!targetDate) {
    // タイムゾーンによるズレを防ぐため、Date.now() から日本の日付文字列を生成する
    const nowJst = new Date(Date.now() + ((new Date().getTimezoneOffset() + (9 * 60)) * 60 * 1000));
    targetDate = nowJst.toISOString().slice(0, 10);
    console.log(`[SSR] fallback to today (JST): ${targetDate}`);
  }

  // Next.js の機能で強制的にキャッシュを無効化する
  // page.tsxの `export const dynamic = 'force-dynamic'` だけでは不十分な場合があるため
  // fetch時のヘッダーに no-store を追加するよう server.ts は修正済み
  // （ここではさらにクエリパラメータを足してAPIへのリクエストを一意にすることも可能だが、
  //   Supabase Client は内部で fetch を使っているため上記で対応済み）

  const [races, user, availableDates] = await Promise.all([
    raceRepo.getRaceList(targetDate),
    createUserRepository().getCurrentUser(),
    raceRepo.getAvailableRaceDates().catch(() => []),
  ]);

  const uiState = deriveUiState(user);
  const policy = derivePolicy(uiState, user?.trialEndsAt ?? null);

  const allInsights = await raceRepo.getFeaturedInsights(targetDate);
  const insights: FeaturedInsights | null = allInsights
    ? (policy.canViewFeaturedInsights
        ? allInsights
        : {
            // 権限がない場合は先頭の1件のみ残して他はフロントに渡さない（マスク用）
            // 先頭固定にすることで keyCompetitors を rank 順（1位先頭）に拡張しても
            // 未ログイン時のプレビュー馬が変わらないようにする。
            keyCompetitors: allInsights.keyCompetitors.slice(0, 1),
            riskyFavorites: allInsights.riskyFavorites.slice(0, 1),
            longshots: allInsights.longshots.slice(0, 1),
          })
    : null;

  return (
    <>
      <Header uiState={uiState} userRole={user?.role} />
      <main className="mx-auto max-w-7xl space-y-6 px-2 py-6 sm:px-4 md:px-6">
        <HeroIntro uiState={uiState} />

        <DateSelector value={targetDate} availableDates={availableDates} />

        <FeaturedInsightsSection insights={insights} uiState={uiState} policy={policy} />

        <section>
          <h1 className="mb-4 text-xl font-bold">レース一覧</h1>
          <RaceListClient races={races} uiState={uiState} policy={policy} />
        </section>
      </main>
      <Footer />
    </>
  );
}
