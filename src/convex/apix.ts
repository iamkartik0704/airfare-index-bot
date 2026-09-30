/**
 * SAFAR read API — the layer the dashboard and the public endpoints share.
 *
 * Every query reads the pipeline `epoch` first, so pressing "Run pipeline"
 * re-observes the market and the whole dashboard recomputes reactively.
 */

import { query } from "./_generated/server";
import { v } from "convex/values";
import {
  AIRPORTS,
  BASKET,
  CARRIERS,
  FARE_CLASSES,
  LEAD_TIMES,
  LEAD_TIME_WEIGHTS,
  OTA_SOURCES,
  ROUTE_WEIGHTS,
  SOURCES,
  routeById,
  type LeadTime,
} from "./lib/basket";
import { ADAPTERS } from "./lib/adapters";
import {
  BASE_DAY,
  atfIndex,
  channelWedge,
  cleanQuotes,
  collectRawQuotes,
  dayIndex,
  isoFromDay,
  routePrice,
  todayDay,
  usdInr,
  demandIndex,
} from "./lib/engine";
import {
  QUOTES_PER_SWEEP,
  STANDARD_WINDOW,
  backtest,
  computeSeries,
  contributions,
  driverRegression,
  leadTimeElasticity,
  monthlySeries,
  sectorHeatmap,
  subIndices,
  weeklySeries,
} from "./lib/index";
import { round } from "./lib/stats";

/** Headline block: the number NSO would quote, with its period-on-period moves. */
export const headline = query({
  args: {},
  handler: async (ctx) => {
    const state = await ctx.db.query("appState").first();
    const epoch = state?.epoch ?? 1;
    const today = todayDay();
    const series = computeSeries(today - STANDARD_WINDOW + 1, today, epoch);
    const last = series[series.length - 1];
    const monthly = monthlySeries(series);
    const prevMonth = monthly[monthly.length - 2];
    const weekAgo = series[Math.max(0, series.length - 8)];

    const routeRows = BASKET.map((r) => {
      const p = routePrice(today, r, epoch);
      const p0 = routePrice(dayIndex(BASE_DAY), r, epoch).price;
      return {
        id: r.id,
        origin: r.origin,
        destination: r.destination,
        distanceKm: r.distanceKm,
        region: r.region,
        weight: round(ROUTE_WEIGHTS[r.id] * 100, 2),
        fare: Math.round(p.price),
        change: round(((p.price - p0) / p0) * 100, 2),
        quality: round(p.quality, 3),
      };
    }).sort((a, b) => b.weight - a.weight);

    return {
      epoch,
      date: last.date,
      index: last.index7d,
      rawToday: last.index,
      nominal: last.nominal,
      dod: last.dod,
      wow: round(((last.index7d - weekAgo.index7d) / weekAgo.index7d) * 100, 2),
      mom: prevMonth ? last.index7d - prevMonth.index : 0,
      momPct: prevMonth ? round(((last.index7d - prevMonth.index) / prevMonth.index) * 100, 2) : 0,
      yoy: last.yoy,
      avgFare: last.avgFare,
      quality: last.quality,
      quotesPerSweep: QUOTES_PER_SWEEP,
      sources: SOURCES.length,
      routes: BASKET.length,
      carriers: CARRIERS.length,
      windows: LEAD_TIMES.length,
      basketRoutes: BASKET.length,
      lastRunAt: state?.lastRunAt ?? null,
      runs: state?.runs ?? 0,
      routeRows,
    };
  },
});

export const dailySeries = query({
  args: { days: v.optional(v.number()) },
  handler: async (ctx, args) => {
    const state = await ctx.db.query("appState").first();
    const epoch = state?.epoch ?? 1;
    const today = todayDay();
    const n = Math.min(Math.max(args.days ?? 400, 60), STANDARD_WINDOW);
    return computeSeries(today - n + 1, today, epoch);
  },
});

export const periodicSeries = query({
  args: { frequency: v.union(v.literal("weekly"), v.literal("monthly")) },
  handler: async (ctx, args) => {
    const state = await ctx.db.query("appState").first();
    const epoch = state?.epoch ?? 1;
    const today = todayDay();
    const pts = computeSeries(today - STANDARD_WINDOW + 1, today, epoch);
    return args.frequency === "weekly" ? weeklySeries(pts) : monthlySeries(pts);
  },
});

export const subIndexSeries = query({
  args: {},
  handler: async (ctx) => {
    const state = await ctx.db.query("appState").first();
    const epoch = state?.epoch ?? 1;
    const today = todayDay();
    return subIndices(computeSeries(today - STANDARD_WINDOW + 1, today, epoch));
  },
});

export const heatmap = query({
  args: {},
  handler: async (ctx) => {
    const state = await ctx.db.query("appState").first();
    const epoch = state?.epoch ?? 1;
    const today = todayDay();
    return sectorHeatmap(today - 200, today, epoch);
  },
});

export const routeContributions = query({
  args: {},
  handler: async (ctx) => {
    const state = await ctx.db.query("appState").first();
    const epoch = state?.epoch ?? 1;
    const today = todayDay();
    return contributions(today - 30, today, epoch);
  },
});

export const elasticity = query({
  args: {},
  handler: async (ctx) => {
    const state = await ctx.db.query("appState").first();
    const epoch = state?.epoch ?? 1;
    const today = todayDay();
    return leadTimeElasticity(today, epoch);
  },
});

export const drivers = query({
  args: {},
  handler: async (ctx) => {
    const state = await ctx.db.query("appState").first();
    const epoch = state?.epoch ?? 1;
    const today = todayDay();
    // Two years of history so the monthly regression has enough changes.
    return driverRegression(computeSeries(today - 760, today, epoch));
  },
});

export const validation = query({
  args: {},
  handler: async (ctx) => {
    const state = await ctx.db.query("appState").first();
    const epoch = state?.epoch ?? 1;
    const today = todayDay();
    const pts = computeSeries(today - STANDARD_WINDOW + 1, today, epoch);
    const bt = backtest(pts, 12);
    const tail = pts.slice(-180);
    return {
      ...bt,
      qualitySeries: tail.map((p) => ({ date: p.date, nominal: p.nominal, real: p.index7d })),
      hedgeRatio: round(tail[tail.length - 1].index7d / tail[tail.length - 1].nominal, 4),
    };
  },
});

export const channelAnalysis = query({
  args: {},
  handler: async (ctx) => {
    const state = await ctx.db.query("appState").first();
    const epoch = state?.epoch ?? 1;
    return channelWedge(todayDay(), epoch);
  },
});

/** Collector registry + last-run audit trail + macro covariates. */
export const pipelineState = query({
  args: {},
  handler: async (ctx) => {
    const state = await ctx.db.query("appState").first();
    const epoch = state?.epoch ?? 1;
    const today = todayDay();
    const runs = await ctx.db
      .query("scrapeRuns")
      .withIndex("by_epoch", (q) => q.eq("epoch", epoch))
      .collect();
    const series = computeSeries(today - 29, today, epoch);

    return {
      epoch,
      lastRunAt: state?.lastRunAt ?? null,
      runs: state?.runs ?? 0,
      adapters: ADAPTERS.map((a) => ({
        id: a.id,
        name: a.name,
        kind: a.kind,
        endpoint: a.endpoint,
        module: a.module,
        render: a.render,
        selectors: a.selectors,
        robots: a.policy.robots,
        rateLimit: a.policy.rateLimit,
        antiBot: a.policy.antiBot,
        retries: a.policy.retries,
        lastRun: runs.find((r) => r.sourceId === a.id) ?? null,
      })),
      totals: {
        sources: SOURCES.length,
        airlines: SOURCES.filter((s) => s.kind === "airline").length,
        otas: SOURCES.filter((s) => s.kind === "ota").length,
        requests: runs.reduce((s, r) => s + r.requests, 0),
        rawQuotes: runs.reduce((s, r) => s + r.rawQuotes, 0),
        blocked: runs.filter((r) => r.status === "blocked").length,
        degraded: runs.filter((r) => r.status === "degraded").length,
        httpErrors: runs.reduce((s, r) => s + r.httpErrors, 0),
        retries: runs.reduce((s, r) => s + r.retries, 0),
        blockEvents: runs.reduce((s, r) => s + r.blockEvents, 0),
        coverage: 0,
      },
      history: series.map((p) => ({ date: p.date, index: p.index, quotes: p.quotes })),
      covariates: {
        atf: atfIndex(today),
        usdInr: round(usdInr(today), 2),
        demand: round(demandIndex(today), 4),
      },
    };
  },
});

/**
 * Raw → cleaned explorer: one sector, one day, the exact funnel the
 * collector produces, so the cleaning story is inspectable, not asserted.
 */
export const explorer = query({
  args: { routeId: v.string(), offsetDays: v.optional(v.number()) },
  handler: async (ctx, args) => {
    const state = await ctx.db.query("appState").first();
    const epoch = state?.epoch ?? 1;
    const route = routeById(args.routeId);
    const day = todayDay() - (args.offsetDays ?? 0);
    const raw = collectRawQuotes(day, route, { leadTime: 7 as LeadTime, epoch });
    const { quotes, report } = cleanQuotes(raw);
    const cell = routePrice(day, route, epoch);

    return {
      date: isoFromDay(day),
      route: {
        id: route.id,
        origin: route.origin,
        destination: route.destination,
        distanceKm: route.distanceKm,
        weight: round(ROUTE_WEIGHTS[route.id] * 100, 2),
      },
      report,
      routeFare: Math.round(cell.price),
      byLead: Object.entries(cell.byLead).map(([k, v2]) => ({
        leadTime: Number(k),
        fare: Math.round(v2),
        premiumPct: round(((v2 / cell.byLead[7] - 1) * 100), 1),
      })),
      carriers: cell.carrierPrices,
      rawSample: raw.slice(0, 24),
      cleanedSample: quotes.slice(0, 24),
    };
  },
});

/** Static methodology + basket metadata (no computation, safe to cache). */
export const methodology = query({
  args: {},
  handler: async () => {
    return {
      basePeriod: BASE_DAY,
      formula:
        "APIx(d) = 100 · Σᵣ wᵣ · [Pᵣ(d)/Pᵣ(0)] · [Q(0)/Q(d)]",
      routes: BASKET.map((r) => ({
        ...r,
        weight: round(ROUTE_WEIGHTS[r.id] * 100, 2),
      })),
      airports: AIRPORTS,
      carriers: CARRIERS,
      fareClasses: FARE_CLASSES,
      leadTimes: LEAD_TIMES.map((l) => ({ leadTime: l, weight: LEAD_TIME_WEIGHTS[l] })),
      sources: SOURCES,
      otaCount: OTA_SOURCES.length,
    };
  },
});

/** Publication ledger. */
export const releases = query({
  args: {},
  handler: async (ctx) => {
    const docs = await ctx.db.query("releases").collect();
    return docs.sort((a, b) => (a.period < b.period ? 1 : -1)).slice(0, 40);
  },
});
