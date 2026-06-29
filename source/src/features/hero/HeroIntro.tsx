import Link from "next/link";
import Image from "next/image";
import { Button } from "@/components/Button";
import type { UiState } from "@/types/user";
import { getActiveSport } from "@/core/sport";

interface Props {
  uiState: UiState;
  /** サンプル閲覧用レースID（既存モック/実データに合わせて差し替え可能） */
  sampleRaceId?: string;
}

const sport = getActiveSport();

// サンプル閲覧用のレースID。モックデータに存在するIDを指定する
const DEFAULT_SAMPLE_RACE_ID =
  sport.id === "kyotei" ? "race-heiwajima-1r" : "race-nakayama-11r";

/**
 * 主 CTA のラベルと遷移先を UiState から決定する。
 * - guest: 新規登録導線
 * - expired: プロ登録導線
 * - trial / pro: マイページ（既存導線）
 */
function resolvePrimaryCta(uiState: UiState) {
  switch (uiState) {
    case "guest":
      return { label: "無料で始める", href: "/signup" };
    case "expired":
      return { label: "プロ登録", href: "/pricing" };
    case "trial":
    case "pro":
      return { label: "マイページへ", href: "/mypage" };
  }
}

export function HeroIntro({
  uiState,
  sampleRaceId = DEFAULT_SAMPLE_RACE_ID,
}: Props) {
  // 未ログイン状態(guest) または 無料会員(trial) のみ表示
  if (uiState !== "guest" && uiState !== "trial") {
    return null;
  }

  const primary = resolvePrimaryCta(uiState);

  return (
    <section
      className="overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm"
      aria-labelledby="hero-title"
    >
      <div className="grid gap-6 p-6 md:grid-cols-2 md:p-8">
        <div className="flex flex-col justify-center">
          <h2
            id="hero-title"
            className="text-2xl font-bold text-gray-900 md:text-3xl"
          >
            CrossFactor AIとは
          </h2>
          <p className="mt-4 whitespace-pre-line text-sm leading-relaxed text-gray-600 md:text-base">
            {sport.labels.heroDescription}
          </p>

          <div className="mt-6 flex flex-wrap gap-3">
            <Link href={primary.href}>
              <Button data-testid="hero-primary-cta">{primary.label}</Button>
            </Link>
            <Link href={`/race/${sampleRaceId}`}>
              <Button variant="secondary" data-testid="hero-sample-cta">
                サンプルを見る
              </Button>
            </Link>
          </div>
        </div>

        <div className="relative aspect-[16/9] overflow-hidden rounded-xl bg-gray-100 md:aspect-auto md:min-h-[220px]">
          <Image
            src="/images/hero-race.png"
            alt={sport.labels.heroImageAlt}
            fill
            sizes="(max-width: 768px) 100vw, 50vw"
            priority
            className="object-cover"
          />
        </div>
      </div>
    </section>
  );
}
