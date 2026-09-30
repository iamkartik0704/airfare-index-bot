/**
 * Display formatting only. Nothing here derives statistics — values are
 * parsed from the API's Decimal strings and rendered in the en-IN locale.
 */

export type Numeric = string | number | null | undefined;

/** Parse an API Decimal string (or number) — `null` when absent/unparseable. */
export function num(v: Numeric): number | null {
  if (v === null || v === undefined || v === "") return null;
  const n = typeof v === "number" ? v : Number(v);
  return Number.isFinite(n) ? n : null;
}

const DASH = "—";

const inrFmt = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });
const intFmt = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });

/** ₹1,05,000 */
export function inr(v: Numeric): string {
  const n = num(v);
  return n === null ? DASH : inrFmt.format(n);
}

/** ₹4.2k — compact axis ticks. */
export function inrCompact(v: Numeric): string {
  const n = num(v);
  if (n === null) return DASH;
  if (Math.abs(n) >= 1000) return `₹${(n / 1000).toFixed(1)}k`;
  return `₹${Math.round(n)}`;
}

export function int(v: Numeric): string {
  const n = num(v);
  return n === null ? DASH : intFmt.format(n);
}

export function fixed(v: Numeric, digits = 2): string {
  const n = num(v);
  return n === null ? DASH : n.toLocaleString("en-IN", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

/** Plain percentage — the API already sends percentage points (e.g. "97.5"). */
export function pct(v: Numeric, digits = 1): string {
  const n = num(v);
  return n === null ? DASH : `${fixed(n, digits)}%`;
}

/** Signed percentage change, e.g. +1.24%. */
export function signedPct(v: Numeric, digits = 2): string {
  const n = num(v);
  if (n === null) return DASH;
  return `${n > 0 ? "+" : ""}${fixed(n, digits)}%`;
}

/** A 0..1 ratio shown as a percentage (e.g. success_rate 0.97 → 97.0%). */
export function ratioPct(v: Numeric, digits = 1): string {
  const n = num(v);
  return n === null ? DASH : `${fixed(n * 100, digits)}%`;
}

export function windowLabel(w: number | string): string {
  const s = String(w);
  return s.startsWith("T+") ? s : `T+${s}`;
}

export function date(v: string | null | undefined): string {
  if (!v) return DASH;
  const d = new Date(v.length === 10 ? `${v}T00:00:00` : v);
  if (Number.isNaN(d.getTime())) return v;
  return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

export function shortDate(v: string | null | undefined): string {
  if (!v) return DASH;
  const d = new Date(v.length === 10 ? `${v}T00:00:00` : v);
  if (Number.isNaN(d.getTime())) return v;
  return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short" });
}

export function monthLabel(v: string | null | undefined): string {
  if (!v) return DASH;
  const d = new Date(`${v.slice(0, 10)}T00:00:00`);
  if (Number.isNaN(d.getTime())) return v;
  return d.toLocaleDateString("en-IN", { month: "short", year: "2-digit" });
}

export function dateTime(v: string | null | undefined): string {
  if (!v) return DASH;
  const d = new Date(v);
  if (Number.isNaN(d.getTime())) return v;
  return d.toLocaleString("en-IN", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}

/** "3 h 12 m" style age for freshness seconds. */
export function duration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined) return DASH;
  const s = Math.max(0, Math.round(seconds));
  if (s < 60) return `${s} s`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m} m`;
  const h = Math.floor(m / 60);
  if (h < 48) return `${h} h ${m % 60} m`;
  return `${Math.floor(h / 24)} d ${h % 24} h`;
}

export function shortId(id: string | null | undefined, n = 8): string {
  return id ? id.slice(0, n) : DASH;
}

export function humanize(key: string): string {
  return key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function cn(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

/** Today's date in IST as YYYY-MM-DD (for date-picker max bounds only). */
export function todayIso(): string {
  return new Date().toLocaleDateString("en-CA", { timeZone: "Asia/Kolkata" });
}

/** Shift an ISO date by whole days (used only to build query-string ranges). */
export function addDays(iso: string, days: number): string {
  const d = new Date(`${iso.slice(0, 10)}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}
