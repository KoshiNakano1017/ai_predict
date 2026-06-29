import type { Metadata, Viewport } from "next";
import "./globals.css";
import { validateEnv } from "@/lib/env";

validateEnv();

export const metadata: Metadata = {
  title: "CrossFactor AI",
  description: "AIによる競馬予測サービス",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  // ピンチズームは許可しつつ、iOS の入力フォーカス時の自動ズームは
  // globals.css 側の font-size:16px で抑止する。
  maximumScale: 5,
  themeColor: "#1a56db",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ja">
      <body className="min-h-screen bg-gray-50 text-gray-900 antialiased">
        {children}
      </body>
    </html>
  );
}
