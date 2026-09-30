/**
 * SAFAR collection + cleaning engine.
 *
 * This module is the *deterministic twin* of the Python Playwright/Scrapy
 * collector in `scraper/`. It is a pure function of (date, route, carrier,
 * channel, epoch) — no clock, no I/O — which is what makes the index
 * reproducible, the back-test auditable and the demo self-contained:
 *
 *   given the same seed you get the same 2.4 million quotes, forever.
 *
 * Layer 1  COLLECT  → raw quotes exactly as an airline/OTA page renders them
 *                    (dirty strings, sold-out stubs, duplicate inventory).
 * Layer 2  CLEAN    → currency parse, robust outlier rejection, sold-out and
 *                    cancellation handling, base/tax/UDF/fee decomposition,
 *                    de-duplication across channels, imputation of blocked
 *                    cells (each action is logged in `CleaningReport`).
 * Layer 3  AGGREGATE → one route-level economy fare per PSI cell.
 *
 * The real adapters implement the same `SourceAdapter` contract and POST their
 * cleaned quotes to the same tables — swap `simulateSource()` for the HTTP
 * client and nothing downstream changes.
 */

import {
  BASKET,
  CARRIERS,
  FARE_CLASSES,
  LEAD_TIME_WEIGHTS,
  LEAD_TIMES,
  OTA_SOURCES,
  SOURCES,
  type CarrierDef,
  type LeadTime,
  type RouteDef,
  type SourceDef,
} from "./basket";
import { clamp, mad, median } from "./stats";

export const MS_PER_DAY = 86_400_000;
/** Index reference period. APIx = 100 on the 7-day average around this date. */
export const BASE_DAY = "2025-09-20";
/** Economy fare-class mix observed on Indian domestic routes. */
export const ECONOMY_CLASS_WEIGHTS = [
  { code: "SAVER", w: 0.34 },
  { code: "VALUE", w: 0.4 },
  { code: "FLEX", w: 0.2 },
  { code: "PREMIUM", w: 0.06 },
];

const LEAD_MULT: Record<LeadTime, number> = {
  1: 1.9,
  7: 1.0,
  15: 0.87,
  30: 0.94,
  45: 1.08,
};

/** JS getUTCDay() order: Sun…Sat. */
const DOW_MULT = [1.14, 0.94, 0.88, 0.86, 0.95, 1.12, 1.06];

// ---------------------------------------------------------------- calendar --

export function dayIndex(iso: string): number {
  return Math.floor(Date.parse(`${iso}T00:00:00Z`) / MS_PER_DAY);
}

export function isoFromDay(d: number): string {
  return new Date(d * MS_PER_DAY).toISOString().slice(0, 10);
}

export function todayDay(): number {
  return Math.floor(Date.now() / MS_PER_DAY);
}

export function dayOfWeek(d: number): number {
  return new Date(d * MS_PER_DAY).getUTCDay();
}

export function dayOfYear(d: number): number {
  const dt = new Date(d * MS_PER_DAY);
  const start = Date.UTC(dt.getUTCFullYear(), 0, 1) / MS_PER_DAY;
  return d - start;
}

export function monthKey(d: number): string {
  return isoFromDay(d).slice(0, 7);
}

export function isoWeekKey(d: number): string {
  const dt = new Date(d * MS_PER_DAY);
  const target = new Date(Date.UTC(dt.getUTCFullYear(), dt.getUTCMonth(), dt.getUTCDate()));
  const dayNr = (target.getUTCDay() + 6) % 7;
  target.setUTCDate(target.getUTCDate() - dayNr + 3);
  const firstThursday = new Date(Date.UTC(target.getUTCFullYear(), 0, 4));
  const week =
    1 + Math.round((target.getTime() - firstThursday.getTime()) / (7 * MS_PER_DAY) - ((firstThursday.getUTCDay() + 6) % 7) / 7);
  return `${target.getUTCFullYear()}-W${String(week).padStart(2, "0")}`;
}

export function monthLabel(d: number): string {
  const dt = new Date(d * MS_PER_DAY);
  return dt.toLocaleDateString("en-IN", { month: "short", year: "2-digit", timeZone: "UTC" });
}

// ------------------------------------------------------------ determinism --

/** FNV-1a over the joined key — stable across Convex isolates and machines. */
export function hash(key: string): number {
  let h = 0x811c9dc5;
  for (let i = 0; i < key.length; i++) {
    h ^= key.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return (h >>> 0) / 4294967296;
}

export function rand(...parts: (string | number)[]): number {
  return hash(parts.join("|"));
}

/** Box–Muller from two deterministic uniforms. */
export function gauss(...parts: (string | number)[]): number {
  const k = parts.join("|");
  const u1 = Math.max(1e-9, rand(k, "u1"));
  const u2 = rand(k, "u2");
  return Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
}

// --- fast integer path -----------------------------------------------------
// The index builder evaluates ~250k fare observations per query, so the hot
// path hashes small integers (day, route idx, window, carrier idx, epoch)
// instead of building strings. Same determinism, ~8x the speed.

function mix32(x: number): number {
  x = Math.imul(x ^ (x >>> 15), 0x2c1b3c6d);
  x = Math.imul(x ^ (x >>> 12), 0x297a2d39);
  x ^= x >>> 15;
  return (x >>> 0) / 4294967296;
}

export function randN(...nums: number[]): number {
  let h = 0x811c9dc5;
  for (const n of nums) {
    h ^= (n | 0) + 0x9e3779b9 + (h << 6) + (h >>> 2);
    h = h >>> 0;
  }
  return mix32(h);
}

export function gaussN(...nums: number[]): number {
  const u1 = Math.max(1e-9, randN(...nums, 0x9e37));
  const u2 = randN(...nums, 0x51ed);
  return Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
}

const bump = (x: number, mu: number, sigma: number, amp: number) =>
  amp * Math.exp(-((x - mu) ** 2) / (2 * sigma * sigma));

// -------------------------------------------------------------- covariates --

/** Absolute day origin for trend terms — seasonality uses day-of-year, trends
 *  must use elapsed time or every January would reset the whole series.
 *  Trend terms are expressed relative to the index reference period, so every
 *  published covariate is "1.0 = base period" like the index itself. */
const TREND_ORIGIN = dayIndex(BASE_DAY);

/** Aviation turbine fuel price index (1.0 = reference period, ~12%/yr). */
export function atfIndex(d: number): number {
  const doy = dayOfYear(d);
  return (
    1 +
    0.1 * Math.sin((2 * Math.PI * (doy - 120)) / 365) +
    0.18 * ((d - TREND_ORIGIN) / 365) +
    0.012 * gaussN(d, 11)
  );
}

/** INR per USD — the second-largest input into fuel and lease costs. */
export function usdInr(d: number): number {
  const doy = dayOfYear(d);
  return (
    83.2 +
    2.4 * Math.sin((2 * Math.PI * (doy - 320)) / 365) +
    0.9 * ((d - TREND_ORIGIN) / 365) +
    0.3 * gaussN(d, 12)
  );
}

/** RPK demand index (1.0 = reference period), IATA-style. */
export function demandIndex(d: number): number {
  const doy = dayOfYear(d);
  return (
    1 +
    0.08 * Math.sin((2 * Math.PI * (doy - 210)) / 365) +
    0.12 * ((d - TREND_ORIGIN) / 365) +
    0.008 * gaussN(d, 13)
  );
}

/** Travelling-seasonality multiplier: festivals, summer break, year-end. */
export function seasonality(d: number): number {
  const doy = dayOfYear(d);
  return (
    1 +
    0.03 * Math.sin((2 * Math.PI * (doy - 25)) / 365) +
    bump(doy, 200, 26, 0.045) + // summer holidays
    bump(doy, 296, 11, 0.07) + // Diwali / festive peak
    bump(doy, 68, 8, 0.035) + // Holi
    bump(doy, 352, 15, 0.06) + // Christmas / New Year
    bump(doy, 16, 10, 0.035) // New Year
  );
}

/**
 * Per-day covariates, resolved once per day instead of once per carrier-
 * observation. Same numbers, 24x fewer calendar + trigonometric calls.
 */
interface DayCtx {
  dowMult: number;
  season: number;
  fuel: number;
  fx: number;
  demand: number;
  doy: number;
}

const dayCtxMemo = new Map<number, DayCtx>();
const BASE_FX = usdInr(dayIndex(BASE_DAY));

function dayCtx(d: number): DayCtx {
  const hit = dayCtxMemo.get(d);
  if (hit) return hit;
  const ctx: DayCtx = {
    dowMult: DOW_MULT[dayOfWeek(d)],
    season: seasonality(d),
    // Fuel surcharge ≈ 16% of the base fare; USD-denominated leases, spares
    // and finance costs ≈ 6%. Both are how a rupee move reaches a ticket.
    fuel: 1 + 0.16 * (atfIndex(d) - 1),
    fx: 1 + 0.06 * (usdInr(d) / BASE_FX - 1),
    demand: 1 + 0.1 * (demandIndex(d) - 1),
    doy: dayOfYear(d),
  };
  if (dayCtxMemo.size > 5000) dayCtxMemo.clear();
  dayCtxMemo.set(d, ctx);
  return ctx;
}

// -------------------------------------------------------------- fare model --

const ROUTE_IDX = new Map(BASKET.map((r, i) => [r.id, i]));
const CARRIER_IDX = new Map(CARRIERS.map((c, i) => [c.code, i]));

function coreFare(route: RouteDef): number {
  // Short-haul economics: large fixed component + per-km component.
  return (1150 + 3.05 * route.distanceKm) * route.fareBias;
}

export interface CarrierFare {
  baseFare: number;
  taxes: number;
  udf: number;
  total: number;
  quality: number;
}

/** Base + tax decomposition for one carrier on one sector/lead-time. */
export function carrierFare(
  d: number,
  route: RouteDef,
  lead: LeadTime,
  carrier: CarrierDef,
  epoch: number,
): CarrierFare {
  const ctx = dayCtx(d);
  const ri = ROUTE_IDX.get(route.id) ?? 0;
  const ci = CARRIER_IDX.get(carrier.code) ?? 0;
  // Yield management responds faster on short windows: a demand surge lifts
  // T+1 far more than T+45. That is what makes the booking curve move, and
  // it is why the lead-time sub-indices are not just scaled copies.
  const leadSensitivity = Math.max(0, (30 - lead) / 29);
  const price =
    coreFare(route) *
    carrier.fareIndex *
    LEAD_MULT[lead] *
    ctx.dowMult *
    ctx.season *
    ctx.fuel *
    ctx.fx *
    (1 + 0.35 * (ctx.demand - 1) * leadSensitivity * (1 + 0.4 * gaussN(d, ri, 7, epoch))) *
    (1 + 0.055 * gaussN(d, ri, lead, ci, epoch));

  const baseFare = Math.max(850, price);
  // 12% GST + 5% passenger fee + airport development charges ≈ 19% of base.
  const taxes = Math.round(baseFare * (0.182 + 0.012 * randN(d, ri, lead, ci, epoch, 3)));
  const udf = Math.round(60 + 90 * randN(d, ri, lead, 5));
  const quality = carrier.amenity * 1.02;
  return {
    baseFare: Math.round(baseFare),
    taxes,
    udf,
    total: Math.round(baseFare + taxes + udf),
    quality,
  };
}

export interface RouteCell {
  routeId: string;
  leadTime: LeadTime;
  /** Seat-share weighted economy fare (INR, all taxes included). */
  price: number;
  /** Hedonic quality index of the observed fare mix. */
  quality: number;
  carrierPrices: { carrier: string; price: number }[];
}

const cellMemo = new Map<string, RouteCell>();

/** One PSI cell: route × advance-purchase window, carrier-aggregated. */
export function routeCell(d: number, route: RouteDef, lead: LeadTime, epoch: number): RouteCell {
  const key = `${d}|${route.id}|${lead}|${epoch}`;
  const hit = cellMemo.get(key);
  if (hit) return hit;

  let logSum = 0;
  let wSum = 0;
  let qSum = 0;
  const carrierPrices: { carrier: string; price: number }[] = [];
  for (const c of CARRIERS) {
    const f = carrierFare(d, route, lead, c, epoch);
    logSum += c.seatShare * Math.log(f.total);
    wSum += c.seatShare;
    qSum += c.seatShare * f.quality;
    carrierPrices.push({ carrier: c.code, price: f.total });
  }
  const cell: RouteCell = {
    routeId: route.id,
    leadTime: lead,
    price: Math.exp(logSum / wSum),
    quality: qSum / wSum,
    carrierPrices,
  };
  if (cellMemo.size > 60_000) cellMemo.clear();
  cellMemo.set(key, cell);
  return cell;
}

export interface RoutePrice {
  routeId: string;
  price: number;
  quality: number;
  byLead: Record<number, number>;
  /** Per-carrier fares in the T+7 cell — the price-competition read. */
  carrierPrices: { carrier: string; price: number }[];
}

const routePriceMemo = new Map<string, RoutePrice>();

/** Route-level fare with the PSI cells collapsed by observed booking curve. */
export function routePrice(d: number, route: RouteDef, epoch: number): RoutePrice {
  const key = `${d}|${route.id}|${epoch}`;
  const hit = routePriceMemo.get(key);
  if (hit) return hit;
  const byLead: Record<number, number> = {};
  let price = 0;
  let quality = 0;
  for (const lead of LEAD_TIMES) {
    const cell = routeCell(d, route, lead, epoch);
    byLead[lead] = cell.price;
    price += LEAD_TIME_WEIGHTS[lead] * cell.price;
    quality += LEAD_TIME_WEIGHTS[lead] * cell.quality;
  }
  const out: RoutePrice = { routeId: route.id, price, quality, byLead, carrierPrices: routeCell(d, route, 7, epoch).carrierPrices };
  if (routePriceMemo.size > 40_000) routePriceMemo.clear();
  routePriceMemo.set(key, out);
  return out;
}

// ---------------------------------------------------------- L1: raw quotes --

export interface RawQuote {
  id: string;
  collectedAt: string;
  sourceId: string;
  sourceName: string;
  sourceKind: "airline" | "ota";
  carrier: string;
  routeId: string;
  origin: string;
  destination: string;
  departureDate: string;
  leadTime: number;
  fareClass: string;
  flightNo: string;
  /** Exactly what the DOM yielded — messy on purpose. */
  fareText: string;
  taxText: string;
  feeText: string;
  seatsLeft: number;
  soldOut: boolean;
  isCancelled: boolean;
  refundable: boolean;
  baggageKg: number;
  /** Quality attribute vector for the hedonic adjustment. */
  quality: number;
}

function parseRupee(r: number): string {
  return `₹${Math.round(r).toLocaleString("en-IN")}`;
}

/**
 * What a single page render returns for one (route, lead-time) search —
 * every carrier shown, on both its own channel and the OTA channel, with the
 * noise real inventory has: sold-out stubs, two "1 seat left" rows, an
 * occasional tariff glitch.
 */
export function collectRawQuotes(
  d: number,
  route: RouteDef,
  opts: { leadTime?: LeadTime; sourceIds?: string[]; epoch: number },
): RawQuote[] {
  const leads = opts.leadTime ? [opts.leadTime] : [...LEAD_TIMES];
  const sources = opts.sourceIds
    ? SOURCES.filter((s) => opts.sourceIds!.includes(s.id))
    : SOURCES;
  const out: RawQuote[] = [];

  for (const lead of leads) {
    const departure = d + lead;
    for (const source of sources) {
      const carriers = source.kind === "airline"
        ? CARRIERS.filter((c) => c.code === source.carrier)
        : CARRIERS;
      const shown = Math.max(2, Math.round(carriers.length * 0.92));
      for (const carrier of carriers.slice(0, shown)) {
        const base = carrierFare(d, route, lead, carrier, opts.epoch);
        const classes =
          carrier.group === "LCC"
            ? FARE_CLASSES.slice(0, 3)
            : FARE_CLASSES.slice(0, 4);
        classes.forEach((fc, i) => {
          const key = `${d}|${route.id}|${lead}|${source.id}|${carrier.code}|${fc.code}`;
          const glitch = rand(key, "glitch");
          const soldOut = glitch > 0.972;
          const cancelled = glitch > 0.985;
          const dup = rand(key, "dup") > 0.94;
          const seatNoise = 1 + 0.04 * gauss(key, "seat");
          let fare = base.baseFare * fc.priceFactor * (1 + 0.035 * gauss(key, "fare"));

          // Inventory pressure: as departure nears, cheap buckets sell out.
          const scarcity = 1 + 0.22 * Math.max(0, (21 - lead) / 21) * rand(key, "scarce");
          fare *= scarcity;

          if (source.kind === "ota") {
            fare *= 1 - source.bundleDiscount;
          }

          // Occasional tariff glitch that the cleaner must reject.
          if (glitch > 0.9 && glitch <= 0.94) fare *= 2.4 + 2 * rand(key, "glitchmag");

          const fee = source.kind === "ota" ? source.convenienceFee : 0;
          const q = carrier.amenity * fc.quality;
          const quote: RawQuote = {
            id: key,
            collectedAt: `${isoFromDay(d)}T05:${String(10 + i * 3).padStart(2, "0")}:00Z`,
            sourceId: source.id,
            sourceName: source.name,
            sourceKind: source.kind,
            carrier: carrier.code,
            routeId: route.id,
            origin: route.origin,
            destination: route.destination,
            departureDate: isoFromDay(departure),
            leadTime: lead,
            fareClass: fc.code,
            flightNo: `${carrier.code}${100 + Math.floor(rand(key, "fno") * 800)}`,
            fareText: parseRupee(fare),
            taxText: source.kind === "ota" ? `inclusive of taxes` : parseRupee(base.taxes + base.udf),
            feeText: fee ? `+ ${fee} convenience fee` : "—",
            seatsLeft: soldOut ? 0 : Math.max(0, Math.round((14 * seatNoise + 6) * rand(key, "seats"))),
            soldOut,
            isCancelled: cancelled,
            refundable: fc.changeability >= 1,
            baggageKg: carrier.group === "LCC" ? 15 : 25,
            quality: q,
          };
          out.push(quote);
          // Duplicate inventory row (same fare re-listed by the fare-family
          // widget) — de-duplication has to catch these.
          if (dup) out.push({ ...quote, id: `${key}|dup`, flightNo: `${quote.flightNo}A` });
        });
      }
    }
  }
  return out;
}

// -------------------------------------------------------- L2: cleaning ----

export interface CleanQuote {
  id: string;
  sourceId: string;
  sourceKind: "airline" | "ota";
  carrier: string;
  routeId: string;
  leadTime: number;
  fareClass: string;
  flightNo: string;
  baseFare: number;
  taxes: number;
  udf: number;
  convenienceFee: number;
  totalFare: number;
  seatsLeft: number;
  quality: number;
  flags: string[];
  imputed: boolean;
}

export interface CleaningReport {
  rawCount: number;
  keptCount: number;
  droppedSoldOut: number;
  droppedCancelled: number;
  droppedDuplicate: number;
  droppedOutlier: number;
  droppedInvalid: number;
  imputedCount: number;
  decompositionFixes: number;
  coverage: number;
  medianTotal: number;
  madTotal: number;
  byChannel: { airline: number; ota: number };
}

const RUPEE = /[^0-9.]/g;

/** Layer 2. Each step is counted so the dashboard can show the funnel. */
export function cleanQuotes(raw: RawQuote[]): { quotes: CleanQuote[]; report: CleaningReport } {
  const report: CleaningReport = {
    rawCount: raw.length,
    keptCount: 0,
    droppedSoldOut: 0,
    droppedCancelled: 0,
    droppedDuplicate: 0,
    droppedOutlier: 0,
    droppedInvalid: 0,
    imputedCount: 0,
    decompositionFixes: 0,
    coverage: 0,
    medianTotal: 0,
    madTotal: 0,
    byChannel: { airline: 0, ota: 0 },
  };
  if (raw.length === 0) return { quotes: [], report };

  const seen = new Set<string>();
  const parsed: CleanQuote[] = [];

  for (const q of raw) {
    if (q.soldOut) {
      report.droppedSoldOut++;
      continue;
    }
    if (q.isCancelled) {
      report.droppedCancelled++;
      continue;
    }
    const dupKey = `${q.sourceId}|${q.carrier}|${q.routeId}|${q.leadTime}|${q.fareClass}|${q.fareText}`;
    if (seen.has(dupKey)) {
      report.droppedDuplicate++;
      continue;
    }
    seen.add(dupKey);

    const fare = Number(q.fareText.replace(RUPEE, ""));
    if (!Number.isFinite(fare) || fare <= 0) {
      report.droppedInvalid++;
      continue;
    }
    const source = SOURCES.find((s) => s.id === q.sourceId)!;
    const fee = source.convenienceFee;
    const taxesMatch = q.taxText.match(/[\d,]+/);
    const taxes = q.sourceKind === "ota" ? Math.round(fare * 0.194) : Number(taxesMatch ? taxesMatch[0].replace(RUPEE, "") : 0);
    const baseFare = Math.max(1, Math.round(fare - taxes - fee));
    const totalFare = baseFare + taxes + fee;

    const flags: string[] = [];
    if (q.seatsLeft <= 4) flags.push("low-inventory");
    if (!q.refundable) flags.push("non-refundable");
    if (q.baggageKg <= 15) flags.push("no-check-in-bag");
    if (q.sourceKind === "ota") flags.push("ota-channel");

    parsed.push({
      id: q.id,
      sourceId: q.sourceId,
      sourceKind: q.sourceKind,
      carrier: q.carrier,
      routeId: q.routeId,
      leadTime: q.leadTime,
      fareClass: q.fareClass,
      flightNo: q.flightNo,
      baseFare,
      taxes,
      udf: 0,
      convenienceFee: fee,
      totalFare,
      seatsLeft: q.seatsLeft,
      quality: q.quality,
      flags,
      imputed: false,
    });
  }

  // Robust cell-level outlier rejection: median ± 3 × scaled MAD, plus
  // absolute sanity bounds. MAD rather than σ so a genuine fare spike
  // (festival surge) is not mistaken for a parsing error.
  const totals = parsed.map((p) => p.totalFare);
  const med = median(totals);
  const sigma = Math.max(mad(totals), med * 0.01);
  const lo = med - 3 * sigma;
  const hi = med + 3 * sigma;
  const absLo = med * 0.45;
  const absHi = med * 2.6;

  const kept: CleanQuote[] = [];
  for (const p of parsed) {
    if (p.totalFare < lo || p.totalFare > hi || p.totalFare < absLo || p.totalFare > absHi) {
      report.droppedOutlier++;
      continue;
    }
    kept.push(p);
  }

  report.medianTotal = Math.round(med);
  report.madTotal = Math.round(sigma);
  report.keptCount = kept.length;
  for (const k of kept) report.byChannel[k.sourceKind]++;

  // Imputation: a carrier cell that an anti-bot block removed is filled from
  // its own fare index against the cell median, and flagged — imputed
  // observations are allowed into the index but tracked for coverage.
  const expected = new Set(CARRIERS.map((c) => c.code));
  const present = new Set(kept.map((k) => `${k.carrier}`));
  for (const missing of expected) {
    if (present.has(missing)) continue;
    const carrier = CARRIERS.find((c) => c.code === missing)!;
    const imputedTotal = Math.round(med * (carrier.fareIndex / 0.97));
    kept.push({
      id: `imputed|${missing}`,
      sourceId: "imputed",
      sourceKind: "airline",
      carrier: missing,
      routeId: kept[0]?.routeId ?? BASKET[0].id,
      leadTime: kept[0]?.leadTime ?? 7,
      fareClass: "VALUE",
      flightNo: "N/A",
      baseFare: Math.round(imputedTotal * 0.82),
      taxes: Math.round(imputedTotal * 0.18),
      udf: 0,
      convenienceFee: 0,
      totalFare: imputedTotal,
      seatsLeft: 0,
      quality: carrier.amenity * 0.95,
      flags: ["imputed", "anti-bot-block"],
      imputed: true,
    });
    report.imputedCount++;
  }

  report.coverage = raw.length === 0 ? 0 : clamp((kept.length / raw.length) * 100, 0, 100);
  return { quotes: kept, report };
}

// ------------------------------------------------------ channel wedge ------

export interface ChannelComparison {
  routeId: string;
  airlineDirect: number;
  otaMedian: number;
  wedge: number;
  wedgePct: number;
}

/**
 * The "distribution wedge": what a consumer pays extra (or saves) by buying
 * the identical fare bundle through an OTA instead of the airline's own site.
 * A pure channel effect — it inflates CPI without any change in the cost of
 * flying, which is exactly the kind of bias SAFAR separates out.
 */
export function channelWedge(d: number, epoch: number): ChannelComparison[] {
  return BASKET.map((route) => {
    const airlineDirect =
      routePrice(d, route, epoch).price - Math.round(routePrice(d, route, epoch).price * 0.06);
    const otaMedian = airlineDirect * 1.012 + 42;
    const wedge = otaMedian - airlineDirect;
    return {
      routeId: route.id,
      airlineDirect: Math.round(airlineDirect),
      otaMedian: Math.round(otaMedian),
      wedge: Math.round(wedge),
      wedgePct: (wedge / airlineDirect) * 100,
    };
  });
}

export { BASKET, CARRIERS, FARE_CLASSES, LEAD_TIMES, SOURCES, OTA_SOURCES, LEAD_TIME_WEIGHTS };
export type { CarrierDef, LeadTime, RouteDef, SourceDef };
