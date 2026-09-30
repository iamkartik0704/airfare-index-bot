/**
 * SAFAR pipeline control plane.
 *
 * `runSweep` is what the dashboard's "Run pipeline" button calls. In
 * production this is the Airflow/Cron trigger for the Scrapy cluster; here it
 * bumps the observation epoch, records one audit row per source, and the
 * deterministic engine re-observes the market — every index, chart and table
 * in the app then recomputes reactively from Convex.
 */

import { mutation } from "./_generated/server";
import { v } from "convex/values";
import { ADAPTERS, simulateSweep } from "./lib/adapters";
import { BASKET } from "./lib/basket";
import { isoFromDay, todayDay } from "./lib/engine";
import { computeSeries } from "./lib/index";
import { round } from "./lib/stats";

export const runSweep = mutation({
  args: { date: v.optional(v.string()) },
  handler: async (ctx, args) => {
    const state = await ctx.db.query("appState").first();
    const epoch = (state?.epoch ?? 1) + 1;
    const day = args.date ? Math.floor(Date.parse(`${args.date}T00:00:00Z`) / 86_400_000) : todayDay();
    const date = isoFromDay(day);

    const existing = await ctx.db
      .query("scrapeRuns")
      .withIndex("by_epoch", (q) => q.eq("epoch", epoch))
      .collect();
    for (const row of existing) await ctx.db.delete(row._id);

    let quotes = 0;
    let blocked = 0;
    for (const adapter of ADAPTERS) {
      const sweep = simulateSweep(adapter, day, epoch, BASKET);
      quotes += sweep.rawQuotes;
      if (sweep.status === "blocked") blocked++;
      await ctx.db.insert("scrapeRuns", {
        epoch,
        date,
        sourceId: sweep.sourceId,
        sourceName: sweep.sourceName,
        kind: sweep.kind,
        status: sweep.status,
        startedAt: sweep.startedAt,
        durationMs: sweep.durationMs,
        requests: sweep.requests,
        rawQuotes: sweep.rawQuotes,
        httpErrors: sweep.httpErrors,
        retries: sweep.retries,
        blockEvents: sweep.blockEvents,
        robotsAllowed: sweep.robotsAllowed,
        crawlDelaySec: sweep.crawlDelaySec,
        rateLimitPerMin: sweep.rateLimitPerMin,
        notes: sweep.notes,
        hue: sweep.hue,
      });
    }

    const now = new Date().toISOString();
    if (state) {
      await ctx.db.patch(state._id, { epoch, lastRunAt: now, lastRunDate: date, runs: (state.runs ?? 0) + 1 });
    } else {
      await ctx.db.insert("appState", { epoch, lastRunAt: now, lastRunDate: date, runs: 1 });
    }

    const series = computeSeries(day - 1, day, epoch);
    const latest = series[series.length - 1];

    return {
      epoch,
      date,
      rawQuotes: quotes,
      blocked,
      sources: ADAPTERS.length,
      index: latest.index,
      changeFromPrevious: round(latest.dod, 3),
    };
  },
});

/** Publish a period to the release ledger (what NSO/RBI would pull from the API). */
export const publishRelease = mutation({
  args: {
    frequency: v.union(v.literal("daily"), v.literal("weekly"), v.literal("monthly")),
    period: v.string(),
    value: v.number(),
    channels: v.optional(v.array(v.string())),
  },
  handler: async (ctx, args) => {
    const samePeriod = await ctx.db
      .query("releases")
      .withIndex("by_period", (q) => q.eq("period", args.period))
      .collect();
    const existing = samePeriod.find((r) => r.frequency === args.frequency);
    const payload = {
      period: args.period,
      frequency: args.frequency,
      value: round(args.value, 2),
      publishedAt: new Date().toISOString(),
      channels: args.channels ?? ["api/v1", "dashboard", "rss"],
    };
    if (existing) {
      await ctx.db.patch(existing._id, payload);
      return existing._id;
    }
    return await ctx.db.insert("releases", payload);
  },
});

/** Register a consumer key for the public API. The hash is what gets stored. */
export const registerApiKey = mutation({
  args: { label: v.string(), org: v.string(), keyHash: v.string(), scopes: v.optional(v.array(v.string())) },
  handler: async (ctx, args) => {
    return await ctx.db.insert("apiKeys", {
      label: args.label,
      keyHash: args.keyHash,
      org: args.org,
      createdAt: new Date().toISOString(),
      scopes: args.scopes ?? ["index:read", "routes:read", "backtest:read"],
    });
  },
});
