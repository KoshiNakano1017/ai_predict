"use client";

import { useState } from "react";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { createClient } from "@/lib/supabase/browser";
import { logger } from "@/lib/logger";

export function ForgotPasswordForm() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const supabase = createClient();
      const redirectTo = `${window.location.origin}/auth/callback?next=/reset-password`;

      const { error: resetError } = await supabase.auth.resetPasswordForEmail(
        email,
        { redirectTo },
      );

      if (resetError) {
        setError(resetError.message);
        return;
      }

      // メールアドレスの存在有無を漏らさないため、成功時は常に同じ案内を表示する
      setSent(true);
    } catch (e) {
      logger.error("ForgotPasswordForm", "Unexpected error", e);
      setError("予期しないエラーが発生しました。");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card className="mx-auto w-full max-w-md p-6 sm:p-8">
      <h1 className="mb-2 text-center text-2xl font-bold text-gray-900">
        パスワード再設定
      </h1>

      {sent ? (
        <div className="mt-4 space-y-4 text-center">
          <p className="rounded-md bg-green-50 p-3 text-sm text-green-700">
            ご入力のメールアドレス宛に、パスワード再設定用のリンクをお送りしました。メールをご確認ください。
          </p>
          <p className="text-sm text-gray-500">
            メールが届かない場合は、迷惑メールフォルダもご確認ください。
          </p>
          <a href="/login" className="text-sm text-brand-primary hover:underline">
            ログイン画面に戻る
          </a>
        </div>
      ) : (
        <>
          <p className="mb-6 text-center text-sm text-gray-500">
            登録済みのメールアドレスを入力してください。再設定用のリンクをお送りします。
          </p>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label
                htmlFor="email"
                className="mb-1 block text-sm font-medium text-gray-700"
              >
                メールアドレス
              </label>
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-primary focus:outline-none focus:ring-1 focus:ring-brand-primary"
                placeholder="you@example.com"
              />
            </div>

            {error && (
              <p className="rounded-md bg-red-50 p-3 text-sm text-red-700">
                {error}
              </p>
            )}

            <Button
              type="submit"
              disabled={loading}
              className="w-full"
              data-testid="forgot-password-submit"
            >
              {loading ? "送信中…" : "再設定リンクを送信"}
            </Button>
          </form>

          <p className="mt-6 text-center text-sm text-gray-500">
            <a href="/login" className="text-brand-primary hover:underline">
              ログイン画面に戻る
            </a>
          </p>
        </>
      )}
    </Card>
  );
}
