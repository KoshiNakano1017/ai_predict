import type { Metadata } from "next";
import { AuthForm } from "@/features/auth/AuthForm";

export const metadata: Metadata = { title: "新規登録 | CrossFactor AI" };

interface Props {
  searchParams: Promise<{ returnTo?: string }>;
}

export default async function SignUpPage({ searchParams }: Props) {
  const params = await searchParams;
  return <AuthForm mode="signup" returnTo={params.returnTo} />;
}
