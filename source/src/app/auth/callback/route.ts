import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { logger } from "@/lib/logger";

/**
 * Supabase Auth の email confirmation callback。
 * メール認証リンクのクリック後にここへリダイレクトされる。
 */
export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");
  const next = searchParams.get("next") ?? "/";

  if (code) {
    try {
      const supabase = await createClient();
      const { error } = await supabase.auth.exchangeCodeForSession(code);
      if (!error) {
        return NextResponse.redirect(`${origin}${next}`);
      }
      logger.warn("AuthCallback", "code exchange failed", error);
    } catch (e) {
      logger.error("AuthCallback", "unexpected error", e);
    }
  }

  return NextResponse.redirect(`${origin}/login?error=auth_callback_failed`);
}
