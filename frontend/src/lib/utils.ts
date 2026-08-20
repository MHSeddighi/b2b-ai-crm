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
