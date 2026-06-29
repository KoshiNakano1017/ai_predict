import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { Card } from "@/components/Card";
import { createUserRepository } from "@/lib/repositories/user";
import { deriveUiState } from "@/types/user";

export const metadata: Metadata = { title: "マイページ | CrossFactor AI" };

export default async function MyPage() {
  const user = await createUserRepository().getCurrentUser();

  if (!user) {
    redirect("/login?returnTo=%2Fmypage");
  }

  const uiState = deriveUiState(user);

  return (
    <>
      <Header uiState={uiState} userRole={user.role} />
      <main className="mx-auto max-w-5xl px-4 py-6">
        <h1 className="mb-4 text-xl font-bold">マイページ</h1>
        <Card className="space-y-2 p-4 sm:p-6">
          <p className="text-sm text-gray-600">ログイン中のアカウント情報</p>
          <p className="break-anywhere">
            <span className="font-medium">メール: </span>
            {user.email}
          </p>
          <p>
            <span className="font-medium">プラン: </span>
            {user.plan}
          </p>
          <p>
            <span className="font-medium">権限: </span>
            {user.role}
          </p>
        </Card>
      </main>
      <Footer />
    </>
  );
}
