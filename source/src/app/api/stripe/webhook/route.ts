import { NextRequest, NextResponse } from "next/server";
import Stripe from "stripe";
import { createClient } from "@supabase/supabase-js";
import { env } from "@/lib/env";
import { logger } from "@/lib/logger";

const TAG = "StripeWebhook";

/**
 * Supabase service_role client — RLS をバイパスして users テーブルを更新する。
 * Webhook は Stripe サーバーからの呼び出しなのでユーザーセッションが存在しない。
 */
function getAdminClient() {
  const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!serviceRoleKey) {
    throw new Error("SUPABASE_SERVICE_ROLE_KEY is not set");
  }
  return createClient(env.supabaseUrl, serviceRoleKey);
}

export async function POST(request: NextRequest) {
  if (!env.stripeSecretKey || !env.stripeWebhookSecret) {
    return NextResponse.json(
      { error: "Stripe is not configured" },
      { status: 503 },
    );
  }

  const stripe = new Stripe(env.stripeSecretKey);
  const body = await request.text();
  const signature = request.headers.get("stripe-signature");

  if (!signature) {
    return NextResponse.json({ error: "Missing signature" }, { status: 400 });
  }

  let event: Stripe.Event;
  try {
    event = stripe.webhooks.constructEvent(
      body,
      signature,
      env.stripeWebhookSecret,
    );
  } catch (err) {
    logger.error(TAG, "Signature verification failed", err);
    return NextResponse.json({ error: "Invalid signature" }, { status: 400 });
  }

  try {
    const supabase = getAdminClient();

    switch (event.type) {
      case "checkout.session.completed": {
        const session = event.data.object as Stripe.Checkout.Session;
        const userId = session.client_reference_id;
        if (!userId) break;

        const { error } = await supabase
          .from("users")
          .update({
            plan: "pro",
            stripe_customer_id: session.customer as string,
            stripe_subscription_id: session.subscription as string,
          })
          .eq("id", userId);

        if (error) logger.error(TAG, "Failed to upgrade user", error);
        else logger.info(TAG, `User ${userId} upgraded to pro`);
        break;
      }

      case "customer.subscription.updated": {
        const sub = event.data.object as Stripe.Subscription;
        if (sub.status === "active") {
          await supabase
            .from("users")
            .update({ plan: "pro" })
            .eq("stripe_subscription_id", sub.id);
        } else if (
          sub.status === "canceled" ||
          sub.status === "unpaid" ||
          sub.status === "past_due"
        ) {
          await supabase
            .from("users")
            .update({ plan: "expired" })
            .eq("stripe_subscription_id", sub.id);
        }
        break;
      }

      case "customer.subscription.deleted": {
        const sub = event.data.object as Stripe.Subscription;
        const { error } = await supabase
          .from("users")
          .update({ plan: "expired" })
          .eq("stripe_subscription_id", sub.id);

        if (error) logger.error(TAG, "Failed to downgrade user", error);
        else logger.info(TAG, `Subscription ${sub.id} deleted, user expired`);
        break;
      }

      default:
        logger.debug(TAG, `Unhandled event type: ${event.type}`);
    }

    return NextResponse.json({ received: true });
  } catch (e) {
    logger.error(TAG, "Webhook processing failed", e);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 },
    );
  }
}
