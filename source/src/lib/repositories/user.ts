import type { UserRepository } from "./types";
import type { AppUser } from "@/types/user";
import { createClient } from "@/lib/supabase/server";
import { logger } from "@/lib/logger";

export class SupabaseUserRepository implements UserRepository {
  async getCurrentUser(): Promise<AppUser | null> {
    try {
      const supabase = await createClient();
      const {
        data: { user },
        error,
      } = await supabase.auth.getUser();

      if (error || !user) return null;

      const { data: profile } = await supabase
        .from("users")
        .select("plan, role, trial_ends_at")
        .eq("id", user.id)
        .single();

      return {
        id: user.id,
        email: user.email ?? "",
        plan: profile?.plan ?? "trial",
        role: profile?.role ?? "member",
        trialEndsAt: profile?.trial_ends_at ?? null,
      };
    } catch (e) {
      logger.warn("UserRepository", "getCurrentUser failed, returning null", e);
      return null;
    }
  }
}

export function createUserRepository(): UserRepository {
  return new SupabaseUserRepository();
}
