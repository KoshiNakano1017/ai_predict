import type { Metadata } from "next";
import { AuthForm } from "@/features/auth/AuthForm";

export const metadata: Metadata = { title: "ログイン | CrossFactor AI" };

interface Props {
  searchParams: Promise<{ returnTo?: string }>;
}

export default async function LoginPage({ searchParams }: Props) {
  const params = await searchParams;
  return <AuthForm mode="login" returnTo={params.returnTo} />;
}
