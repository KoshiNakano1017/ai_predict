import type { Metadata } from "next";
import { ResetPasswordForm } from "@/features/auth/ResetPasswordForm";

export const metadata: Metadata = { title: "新しいパスワードの設定 | CrossFactor AI" };

export default function ResetPasswordPage() {
  return <ResetPasswordForm />;
}
