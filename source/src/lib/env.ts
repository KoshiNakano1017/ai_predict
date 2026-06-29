/**
 * 起動時に環境変数の存在を検証し、不足があれば warning を出す。
 * Vercel Preview で動作確認しやすくするための安全弁。
 */
const requiredPublic = [
  "NEXT_PUBLIC_SUPABASE_URL",
  "NEXT_PUBLIC_SUPABASE_ANON_KEY",
] as const;

const requiredServer = [
  "SUPABASE_SERVICE_ROLE_KEY",
  "STRIPE_SECRET_KEY",
  "STRIPE_PRICE_ID",
  "STRIPE_WEBHOOK_SECRET",
] as const;

function check(keys: readonly string[], label: string) {
  const missing = keys.filter((k) => !process.env[k]);
  if (missing.length > 0) {
    console.warn(
      `[env] ${label} の環境変数が未設定です: ${missing.join(", ")}`,
    );
  }
}

export function validateEnv() {
  check(requiredPublic, "Public");
  if (typeof window === "undefined") {
    check(requiredServer, "Server");
  }
}

export const env = {
  supabaseUrl: process.env.NEXT_PUBLIC_SUPABASE_URL ?? "",
  supabaseAnonKey: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "",
  stripeSecretKey: process.env.STRIPE_SECRET_KEY ?? "",
  stripePriceId: process.env.STRIPE_PRICE_ID ?? "",
  stripeWebhookSecret: process.env.STRIPE_WEBHOOK_SECRET ?? "",
  appUrl: process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000",
};
