import type { AppUser } from "@/types/user";

export const MOCK_USERS: Record<string, AppUser> = {
  trial: {
    id: "mock-trial-user",
    email: "trial@example.com",
    plan: "trial",
    role: "member",
    trialEndsAt: new Date(Date.now() + 5 * 86400000).toISOString(),
  },
  expired: {
    id: "mock-expired-user",
    email: "expired@example.com",
    plan: "expired",
    role: "member",
    trialEndsAt: new Date(Date.now() - 86400000).toISOString(),
  },
  pro: {
    id: "mock-pro-user",
    email: "pro@example.com",
    plan: "pro",
    role: "admin",
    trialEndsAt: null,
  },
};
