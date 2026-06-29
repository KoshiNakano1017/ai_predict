import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { env } from "@/lib/env";
import { logger } from "@/lib/logger";

export async function POST() {
  try {
    if (!env.stripeSecretKey || !env.stripePriceId) {
      return NextResponse.json(
        { error: "Stripe is not configured" },
        { status: 503 },
      );
    }

    const supabase = await createClient();
    const {
      data: { user },
    } = await supabase.auth.getUser();

    if (!user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    // Stripe SDK を動的 import して、未設定時のビルドエラーを回避
    const stripe = (await import("stripe")).default;
    const client = new stripe(env.stripeSecretKey);

    const session = await client.checkout.sessions.create({
      mode: "subscription",
      line_items: [{ price: env.stripePriceId, quantity: 1 }],
      success_url: `${env.appUrl}/?checkout=success`,
      cancel_url: `${env.appUrl}/pricing?checkout=cancel`,
      client_reference_id: user.id,
      customer_email: user.email,
    });

    return NextResponse.json({ url: session.url });
  } catch (e) {
    logger.error("StripeCheckout", "session creation failed", e);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 },
    );
  }
}
