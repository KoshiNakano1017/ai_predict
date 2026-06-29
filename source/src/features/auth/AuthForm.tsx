"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { createClient } from "@/lib/supabase/browser";
import { logger } from "@/lib/logger";
import { getActiveSport } from "@/core/sport";

interface Props {
  mode: "signup" | "login";
  returnTo?: string;
}

const sport = getActiveSport();

export function AuthForm({ mode, returnTo }: Props) {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);

  const isSignup = mode === "signup";
  const title = isSignup ? "無料で始める" : "ログイン";
  const subtitle = isSignup ? sport.labels.tagline : null;
  const submitLabel = "ログインリンクを送信";
  const altText = isSignup ? "すでにアカウントをお持ちですか？" : "アカウントをお持ちでないですか？";
  const altLink = isSignup ? "/login" : "/signup";
  const altLabel = isSignup ? "ログイン" : "新規登録";

  async function handleGoogleLogin() {
    try {
      const supabase = createClient();
      await supabase.auth.signInWithOAuth({
        provider: "google",
        options: {
          redirectTo: `${window.location.origin}/auth/callback?next=${returnTo ?? "/"}`,
        },
      });
    } catch (e) {
      logger.error("AuthForm", "Google Auth error", e);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const supabase = createClient();
      // マジックリンク認証に変更
      const { error: authError } = await supabase.auth.signInWithOtp({
        email,
        options: {
          emailRedirectTo: `${window.location.origin}/auth/callback?next=${returnTo ?? "/"}`,
        },
      });

      if (authError) {
        setError(authError.message);
        return;
      }

      setSent(true);
    } catch (e) {
      logger.error("AuthForm", "Unexpected error", e);
      setError("予期しないエラーが発生しました。");
    } finally {
      setLoading(false);
    }
  }

  if (sent) {
    return (
      <Card className="mx-auto w-full max-w-md p-6 sm:p-10 text-center">
        <h1 className="mb-4 text-2xl font-bold text-gray-900">メールを送信しました</h1>
        <p className="text-gray-600">
          {email} 宛にログイン用のリンクを送信しました。<br />
          メール内のリンクをクリックしてログインしてください。
        </p>
      </Card>
    );
  }

  return (
    <Card className="mx-auto w-full max-w-md p-6 sm:p-10 border border-gray-200 shadow-sm rounded-xl">
      <div className="mb-8 text-center">
        <h1 className="text-2xl font-bold text-gray-900">{title}</h1>
        {subtitle && <p className="mt-2 text-sm text-gray-600">{subtitle}</p>}
      </div>

      <button
        type="button"
        onClick={handleGoogleLogin}
        className="mb-6 flex w-full items-center justify-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm font-medium text-gray-700 transition hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-brand-primary focus:ring-offset-1"
      >
        <svg viewBox="0 0 24 24" width="20" height="20" xmlns="http://www.w3.org/2000/svg">
          <g transform="matrix(1, 0, 0, 1, 27.009001, -39.238998)">
            <path fill="#4285F4" d="M -3.264 51.509 C -3.264 50.719 -3.334 49.969 -3.454 49.239 L -14.754 49.239 L -14.754 53.749 L -8.284 53.749 C -8.574 55.229 -9.424 56.479 -10.684 57.329 L -10.684 60.329 L -6.824 60.329 C -4.564 58.239 -3.264 55.159 -3.264 51.509 Z" />
            <path fill="#34A853" d="M -14.754 63.239 C -11.514 63.239 -8.804 62.159 -6.824 60.329 L -10.684 57.329 C -11.764 58.049 -13.134 58.489 -14.754 58.489 C -17.884 58.489 -20.534 56.379 -21.484 53.529 L -25.464 53.529 L -25.464 56.619 C -23.494 60.539 -19.444 63.239 -14.754 63.239 Z" />
            <path fill="#FBBC05" d="M -21.484 53.529 C -21.734 52.809 -21.864 52.039 -21.864 51.239 C -21.864 50.439 -21.724 49.669 -21.484 48.949 L -21.484 45.859 L -25.464 45.859 C -26.284 47.479 -26.754 49.299 -26.754 51.239 C -26.754 53.179 -26.284 54.999 -25.464 56.619 L -21.484 53.529 Z" />
            <path fill="#EA4335" d="M -14.754 43.989 C -12.984 43.989 -11.404 44.599 -10.154 45.789 L -6.734 41.939 C -8.804 40.009 -11.514 38.989 -14.754 38.989 C -19.444 38.989 -23.494 41.689 -25.464 45.859 L -21.484 48.949 C -20.534 46.099 -17.884 43.989 -14.754 43.989 Z" />
          </g>
        </svg>
        Googleで{isSignup ? "登録" : "ログイン"}
      </button>

      <div className="relative mb-6 flex items-center justify-center">
        <div className="w-full border-t border-gray-200"></div>
        <span className="absolute bg-white px-3 text-xs text-gray-500">または</span>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div>
          <label
            htmlFor="email"
            className="mb-2 block text-sm font-bold text-gray-700"
          >
            メールアドレス
          </label>
          <input
            id="email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-4 py-3 text-base text-gray-900 placeholder:text-gray-400 focus:border-blue-600 focus:outline-none focus:ring-1 focus:ring-blue-600"
            placeholder="your@email.com"
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
          className="w-full bg-blue-600 hover:bg-blue-700 py-3 text-base font-bold"
          data-testid={`auth-${mode}-submit`}
        >
          {loading ? "送信中…" : submitLabel}
        </Button>
      </form>

      <p className="mt-8 text-center text-sm text-gray-600">
        {altText} <a href={altLink} className="text-blue-600 font-bold hover:underline">{altLabel}</a>
      </p>
    </Card>
  );
}
