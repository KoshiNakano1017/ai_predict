"use client";

import { Card } from "@/components/Card";
import { Badge } from "@/components/Badge";
import { Button } from "@/components/Button";
import { getActiveSport } from "@/core/sport";

interface Props {
  onCheckout: (billingCycle: "monthly" | "annual") => void;
  loading?: boolean;
}

const sport = getActiveSport();

const FREE_FEATURES = [
  "1日1レース",
  `勝率ランキング（${sport.labels.allEntries}）ソート可能`,
  `期待値ランキング（${sport.labels.allEntries}）ソート可能`,
  `詳細理由（${sport.labels.allEntries}）`,
  "レース評価（A / B / C）",
];

const PRO_FEATURES = [
  `勝率ランキング（${sport.labels.allEntries}・ソート可能）`,
  `期待値ランキング（${sport.labels.allEntries}・ソート可能）`,
  `詳細理由（${sport.labels.allEntries}）`,
  sport.labels.riskyTitle,
  sport.labels.longshotTitle,
  "レース評価（A / B / C）",
];

function FeatureList({ items }: { items: string[] }) {
  return (
    <ul className="mt-4 space-y-2 text-sm text-gray-600">
      {items.map((item) => (
        <li key={item} className="flex items-start gap-2">
          <span className="text-green-500">✓</span>
          {item}
        </li>
      ))}
    </ul>
  );
}

export function PricingCard({ onCheckout, loading }: Props) {
  return (
    <div className="space-y-6">
      {/* 3カードグリッド */}
      <div className="grid gap-6 md:grid-cols-3">
        {/* 無料プラン */}
        <Card className="p-4 sm:p-6">
          <h3 className="text-xl font-bold text-gray-900">無料プラン</h3>
          <p className="mt-1 text-3xl font-extrabold text-gray-900">¥0</p>
          <FeatureList items={FREE_FEATURES} />
        </Card>

        {/* プロプラン（月額）*/}
        <div className="relative">
          <div className="absolute -top-3 left-1/2 -translate-x-1/2">
            <Badge label="おすすめ" color="blue" />
          </div>
          <Card className="relative border-brand-primary p-4 ring-2 ring-brand-primary sm:p-6">
            <h3 className="mt-1 text-xl font-bold text-gray-900">
              プロプラン（月額）
            </h3>
            <p className="mt-1 text-3xl font-extrabold text-gray-900">
              ¥—
              <span className="text-base font-normal text-gray-500"> / 月</span>
            </p>
            <p className="mt-1 text-xs text-gray-400">
              ※ 料金はクライアント確認後に確定
            </p>
            <FeatureList items={PRO_FEATURES} />
            <Button
              onClick={() => onCheckout("monthly")}
              disabled={loading}
              className="mt-6 w-full"
              data-testid="pricing-checkout-monthly"
            >
              {loading ? "処理中…" : "プロで始める"}
            </Button>
          </Card>
        </div>

        {/* プロプラン（年額）*/}
        <Card className="p-4 sm:p-6">
          <h3 className="text-xl font-bold text-gray-900">
            プロプラン（年額）
          </h3>
          <p className="mt-1 text-3xl font-extrabold text-gray-900">
            ¥—
            <span className="text-base font-normal text-gray-500"> / 年</span>
          </p>
          <p className="mt-1 text-xs text-green-600 font-medium">
            実質 ¥— / 月
          </p>
          <FeatureList items={PRO_FEATURES} />
          <Button
            variant="secondary"
            onClick={() => onCheckout("annual")}
            disabled={loading}
            className="mt-6 w-full"
            data-testid="pricing-checkout-annual"
          >
            {loading ? "処理中…" : "プロで始める（年額）"}
          </Button>
        </Card>
      </div>

      {/* 節約メッセージ */}
      <p className="text-center text-sm text-gray-500">
        年額プランで{" "}
        <span className="font-bold text-brand-primary">¥— お得</span>
        （2ヶ月分無料）
      </p>
    </div>
  );
}
