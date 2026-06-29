import { createServerClient, type CookieOptions } from "@supabase/ssr";
import { cookies } from "next/headers";
import { env } from "@/lib/env";

interface CookieToSet {
  name: string;
  value: string;
  options?: CookieOptions;
}

export async function createClient() {
  const cookieStore = await cookies();

  // options 内に global: { fetch: fetch } のように Next.js の fetch キャッシュを無効化する設定を追加
  return createServerClient(env.supabaseUrl, env.supabaseAnonKey, {
    global: {
      fetch: (url: string | URL | Request, options?: RequestInit) => {
        return fetch(url, { ...options, cache: "no-store" });
      },
    },
    cookies: {
      getAll() {
        return cookieStore.getAll();
      },
      setAll(cookiesToSet: CookieToSet[]) {
        try {
          cookiesToSet.forEach(({ name, value, options }) =>
            cookieStore.set(name, value, options),
          );
        } catch {
          // Server Component からの呼び出し時は set できないが、
          // middleware 側で refresh 済みなので無視して問題ない。
        }
      },
    },
  });
}
