"use client";

import { useState } from "react";
import Link from "next/link";
import type { UiState, UserRole } from "@/types/user";
import { Button } from "./Button";

interface Props {
  uiState: UiState;
  userRole?: UserRole | null;
}

export function Header({ uiState, userRole }: Props) {
  const [open, setOpen] = useState(false);
  const close = () => setOpen(false);

  const isMember =
    uiState === "trial" || uiState === "expired" || uiState === "pro";

  return (
    <header className="sticky top-0 z-40 border-b border-gray-200 bg-white">
      <div className="mx-auto flex h-14 max-w-5xl items-center justify-between px-4">
        <Link
          href="/"
          className="text-lg font-bold text-brand-dark sm:text-xl"
          onClick={close}
        >
          CrossFactor AI
        </Link>

        {/* デスクトップ: 横並びナビ (sm 以上) */}
        <nav className="hidden items-center gap-6 sm:flex">
          <NavLinks />
          <div className="flex items-center gap-2">
            <NavActions uiState={uiState} userRole={userRole} isMember={isMember} />
          </div>
        </nav>

        {/* モバイル: ハンバーガー (sm 未満) */}
        <button
          type="button"
          className="flex h-11 w-11 items-center justify-center rounded-lg text-gray-600 transition hover:bg-gray-100 sm:hidden"
          aria-label={open ? "メニューを閉じる" : "メニューを開く"}
          aria-expanded={open}
          aria-controls="mobile-menu"
          onClick={() => setOpen((v) => !v)}
          data-testid="header-menu-toggle"
        >
          {open ? <CloseIcon /> : <MenuIcon />}
        </button>
      </div>

      {/* モバイルメニュー本体 */}
      {open && (
        <div
          id="mobile-menu"
          className="border-t border-gray-100 bg-white sm:hidden"
          data-testid="header-mobile-menu"
        >
          <nav className="mx-auto flex max-w-5xl flex-col gap-1 px-4 py-3">
            <div className="mb-2 flex flex-col gap-3 px-2 py-2">
              <NavLinks onNavigate={close} mobile />
            </div>
            <NavActions
              uiState={uiState}
              userRole={userRole}
              isMember={isMember}
              mobile
              onNavigate={close}
            />
          </nav>
        </div>
      )}
    </header>
  );
}

function NavLinks({ onNavigate, mobile }: { onNavigate?: () => void; mobile?: boolean }) {
  const linkClass = mobile ? "text-base font-medium text-gray-700" : "text-sm font-medium text-gray-600 hover:text-gray-900";
  return (
    <>
      <Link href="/" className={linkClass} onClick={onNavigate}>ホーム</Link>
      <Link href="/pricing" className={linkClass} onClick={onNavigate}>料金</Link>
    </>
  );
}

interface NavActionsProps {
  uiState: UiState;
  userRole?: UserRole | null;
  isMember: boolean;
  mobile?: boolean;
  onNavigate?: () => void;
}

/**
 * デスクトップ(横並び)とモバイル(縦並びメニュー)で共通のアクション群。
 * mobile=true のときは縦並び・フル幅・タップターゲット 44px を担保する。
 */
function NavActions({
  uiState,
  userRole,
  isMember,
  mobile = false,
  onNavigate,
}: NavActionsProps) {
  const fullWidth = mobile ? "w-full justify-center" : "";

  return (
    <>
      {uiState === "guest" && (
        <>
          <Link href="/signup" onClick={onNavigate} className={mobile ? "w-full" : ""}>
            <Button data-testid="header-signup" className={`bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-lg px-5 py-2 ${fullWidth}`}>
              新規登録
            </Button>
          </Link>
          <Link href="/login" onClick={onNavigate} className={mobile ? "w-full" : ""}>
              <Button
                variant="secondary"
                data-testid="header-login"
                className={`font-bold px-5 py-2 ${fullWidth}`}
              >
              ログイン
            </Button>
          </Link>
        </>
      )}

      {isMember && (
        <>
          {userRole === "admin" && (
            <Link
              href="/admin"
              onClick={onNavigate}
              className={mobile ? "w-full" : ""}
            >
              <Button
                variant="ghost"
                data-testid="header-admin"
                className={fullWidth}
              >
                管理画面
              </Button>
            </Link>
          )}

          {mobile ? (
            <Link href="/mypage" onClick={onNavigate} className="w-full">
              <Button variant="ghost" className="w-full justify-center">
                マイページ
              </Button>
            </Link>
          ) : (
            <Link
              href="/mypage"
              className="flex h-9 w-9 items-center justify-center rounded-full bg-gray-200 text-sm font-medium text-gray-600 transition hover:bg-gray-300"
              data-testid="header-avatar"
              aria-label="マイページ"
            >
              U
            </Link>
          )}

          <form
            action="/auth/logout"
            method="post"
            className={mobile ? "w-full" : ""}
          >
            <Button
              type="submit"
              variant="ghost"
              data-testid="header-logout"
              className={fullWidth}
            >
              ログアウト
            </Button>
          </form>
        </>
      )}
    </>
  );
}

function MenuIcon() {
  return (
    <svg
      className="h-6 w-6"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      aria-hidden
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M4 6h16M4 12h16M4 18h16"
      />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg
      className="h-6 w-6"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      aria-hidden
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M6 18L18 6M6 6l12 12"
      />
    </svg>
  );
}
