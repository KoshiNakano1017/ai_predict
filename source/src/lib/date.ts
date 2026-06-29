const WEEKDAYS_JP = ["日", "月", "火", "水", "木", "金", "土"] as const;

/**
 * ISO 日付 (YYYY-MM-DD) を `YYYY年M月D日（曜）` 形式に整形する。
 * タイムゾーン差を出さないよう日付部のみで解釈する。
 */
export function formatJpDate(iso: string): string {
  const [y, m, d] = iso.split("-").map((v) => Number(v));
  if (!y || !m || !d) return iso;
  const dt = new Date(Date.UTC(y, m - 1, d));
  const w = WEEKDAYS_JP[dt.getUTCDay()];
  return `${y}年${m}月${d}日（${w}）`;
}

/** ISO 日付 `YYYY-MM-DD` の今日を返す（ローカルタイム）。 */
export function todayIso(): string {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, "0");
  const d = String(now.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}
