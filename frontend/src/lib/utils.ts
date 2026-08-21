import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Format a number with Persian (fa-IR) digits and separators. */
export function formatNumber(value: number): string {
  return new Intl.NumberFormat("fa-IR", { maximumFractionDigits: 1 }).format(value);
}

export function formatCurrency(value: number): string {
  // Monetary amounts — neutral Persian formatting (no hardcoded currency, since
  // the underlying unit varies). Use compact notation for large values.
  return new Intl.NumberFormat("fa-IR", {
    notation: Math.abs(value) >= 1_000_000 ? "compact" : "standard",
    maximumFractionDigits: 1,
  }).format(value);
}

export function formatCompact(value: number): string {
  return new Intl.NumberFormat("fa-IR", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);
}

export function formatPercent(value: number): string {
  const sign = value > 0 ? "+" : "";
  return `${sign}${new Intl.NumberFormat("fa-IR", { maximumFractionDigits: 1 }).format(value)}٪`;
}

/** Ensure a body/description sentence ends with a Persian period.
 * Titles and subtitles must NOT use this helper. */
export function withDot(text: string): string {
  const t = String(text).trim();
  if (!t) return t;
  return /[.!?؟۔…]$/.test(t) ? t : `${t}.`;
}

/** Gregorian ISO date (YYYY-MM-DD) -> Persian (Jalali) date with Persian digits. */
export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  const m = String(value).match(/^(\d{4})-(\d{1,2})-(\d{1,2})/);
  if (!m) return String(value);
  const [gy, gm, gd] = [Number(m[1]), Number(m[2]), Number(m[3])];
  let jy = gy - 621;
  const leap = (gy % 4 === 0 && gy % 100 !== 0) || gy % 400 === 0;
  const g_days_in_month = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  const j_days_in_month = [31, 31, 31, 31, 31, 31, 30, 30, 30, 30, 30, 29];
  let g_day_of_year =
    gd + g_days_in_month.slice(0, gm - 1).reduce((a, b) => a + b, 0);
  let j_day_of_year = g_day_of_year - 79;
  let jm = 0;
  if (j_day_of_year <= 0) {
    jy -= 1;
    j_day_of_year += leap ? 366 : 365;
  }
  for (let i = 0; i < 12; i++) {
    if (j_day_of_year <= j_days_in_month[i]) {
      jm = i + 1;
      break;
    }
    j_day_of_year -= j_days_in_month[i];
  }
  // Persian digits without the thousands separator — a Jalali year like ۱۳۹۸
  // must never render as ۱٬۳۹۸.
  const fa = (n: number) => new Intl.NumberFormat("fa-IR", { useGrouping: false }).format(n);
  return `${fa(jy)}/${fa(jm)}/${fa(j_day_of_year)}`;
}
