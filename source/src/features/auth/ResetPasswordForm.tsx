"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { createClient } from "@/lib/supabase/browser";
import { logger } from "@/lib/logger";

export function ResetPasswordForm() {
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  // リカバリーリンク経由のセッションが確立しているか
  const [ready, setReady] = useState(false);
  const [sessionError, setSessionError] = useState(false);

  // /auth/callback で code をセッションに交換済みの想定。
  // 念のためセッションの有無を確認し、無効リンクの場合は案内を出す。
  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getSession().then(({ data }) => {
      if (data.session) {
        setReady(true);
      } else {
        setSessionError(true);
      }
    });
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (password !== confirm) {
      setError("パスワードが一致しません。");
      return;
    }

    setLoading(true);
    try {
      const supabase = createClient();
      const { error: updateError } = await supabase.auth.updateUser({
        password,
      });

      if (updateError) {
        setError(updateError.message);
        return;
      }

      setDone(true);
      setTimeout(() => {
        router.push("/");
        router.refresh();
      }, 1500);
    } catch (e) {
      logger.error("ResetPasswordForm", "Unexpected error", e);
      setError("予期しないエラーが発生しました。");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card className="mx-auto w-full max-w-md p-6 sm:p-8">
      <h1 className="mb-6 text-center text-2xl font-bold text-gray-900">
        新しいパスワードの設定
      </h1>

      {done ? (
        <p className="rounded-md bg-green-50 p-3 text-center text-sm text-green-700">
          パスワードを更新しました。トップページへ移動します…
        </p>
      ) : sessionError ? (
        <div className="space-y-4 text-center">
          <p className="rounded-md bg-red-50 p-3 text-sm text-red-700">
            リンクが無効か、有効期限が切れています。お手数ですが、もう一度パスワード再設定をお試しください。
          </p>
          <a
            href="/forgot-password"
            className="text-sm text-brand-primary hover:underline"
          >
            パスワード再設定をやり直す
          </a>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="password"
              className="mb-1 block text-sm font-medium text-gray-700"
            >
              新しいパスワード
            </label>
            <input
              id="password"
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-primary focus:outline-none focus:ring-1 focus:ring-brand-primary"
              placeholder="8文字以上"
            />
          </div>

          <div>
            <label
              htmlFor="confirm"
              className="mb-1 block text-sm font-medium text-gray-700"
            >
              新しいパスワード（確認）
            </label>
            <input
              id="confirm"
              type="password"
              required
              minLength={8}
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-primary focus:outline-none focus:ring-1 focus:ring-brand-primary"
              placeholder="もう一度入力"
            />
          </div>

          {error && (
            <p className="rounded-md bg-red-50 p-3 text-sm text-red-700">
              {error}
            </p>
          )}

          <Button
            type="submit"
            disabled={loading || !ready}
            className="w-full"
            data-testid="reset-password-submit"
          >
            {loading ? "更新中…" : "パスワードを更新"}
          </Button>
        </form>
      )}
    </Card>
  );
}
