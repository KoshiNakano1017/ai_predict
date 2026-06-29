import type { Metadata } from "next";
import { ForgotPasswordForm } from "@/features/auth/ForgotPasswordForm";

export const metadata: Metadata = { title: "パスワード再設定 | CrossFactor AI" };

export default function ForgotPasswordPage() {
  return <ForgotPasswordForm />;
}
