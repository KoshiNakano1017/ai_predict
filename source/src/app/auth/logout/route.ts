import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { logger } from "@/lib/logger";

export async function POST(request: Request) {
  try {
    const supabase = await createClient();
    await supabase.auth.signOut();
  } catch (e) {
    logger.error("AuthLogout", "Failed to sign out", e);
  }

  const origin = new URL(request.url).origin;
  return NextResponse.redirect(`${origin}/login`, { status: 303 });
}
