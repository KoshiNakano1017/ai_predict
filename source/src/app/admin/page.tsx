import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { Card } from "@/components/Card";
import { createUserRepository } from "@/lib/repositories/user";
import { deriveUiState } from "@/types/user";

export const metadata: Metadata = { title: "管理画面 | CrossFactor AI" };

export default async function AdminPage() {
  const user = await createUserRepository().getCurrentUser();

  if (!user) {
    redirect("/login?returnTo=%2Fadmin");
  }

  if (user.role !== "admin") {
    redirect("/");
  }

  const uiState = deriveUiState(user);

  return (
    <>
      <Header uiState={uiState} userRole={user.role} />
      <main className="mx-auto max-w-5xl px-4 py-6">
        <h1 className="mb-4 text-xl font-bold">管理画面</h1>
        <Card className="space-y-2 p-4 sm:p-6">
          <p className="text-sm text-gray-600">
            この画面は admin 権限ユーザーのみアクセスできます。
          </p>
          <p className="break-anywhere">
            <span className="font-medium">ログイン中: </span>
            {user.email}
          </p>
        </Card>
      </main>
      <Footer />
    </>
  );
}
