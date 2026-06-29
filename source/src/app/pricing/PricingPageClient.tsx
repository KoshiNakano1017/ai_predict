"use client";

import { useState } from "react";
import { PricingCard } from "@/features/pricing/PricingCard";
import { logger } from "@/lib/logger";

export function PricingPageClient() {
  const [loading, setLoading] = useState(false);

  async function handleCheckout(billingCycle: "monthly" | "annual") {
    setLoading(true);
    try {
      const res = await fetch("/api/stripe/checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ billingCycle }),
      });
      const data = await res.json();
      if (data.url) {
        window.location.href = data.url;
      } else {
        logger.warn("PricingPage", "Checkout URL not returned", data);
        alert("決済画面の生成に失敗しました。しばらくしてからお試しください。");
      }
    } catch (e) {
      logger.error("PricingPage", "Checkout error", e);
      alert("エラーが発生しました。");
    } finally {
      setLoading(false);
    }
  }

  return <PricingCard onCheckout={handleCheckout} loading={loading} />;
}
