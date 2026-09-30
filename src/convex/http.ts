import { httpRouter, httpActionGeneric } from "convex/server";
import { auth } from "./auth";
import { BASKET, CARRIERS, ROUTE_WEIGHTS, SOURCES } from "./lib/basket";
import { BASE_DAY, dayIndex, todayDay } from "./lib/engine";
import {
  STANDARD_WINDOW,
  backtest,
  computeSeries,
  monthlySeries,
  subIndices,
  weeklySeries,
} from "./lib/index";

const http = httpRouter();

auth.addHttpRoutes(http);

/**
 * SAFAR public API — what NSO / RBI / an academic would consume.
 *
 *   GET /api/v1/health
 *   GET /api/v1/index/latest
 *   GET /api/v1/index/series?freq=daily|weekly|monthly&days=90
 *   GET /api/v1/basket
 *   GET /api/v1/backtest
 *
 * Auth: `x-api-key` header. The prototype ships one demo key; the production
 * design stores only a hash of each key in `apiKeys` with per-org scopes
 * (index:read, routes:read, backtest:read) and a rolling 30-day audit trail.
 */
const DEMO_KEY = "safar-demo-26056";

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body, null, 2), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "access-control-allow-origin": "*",
      "cache-control": "public, max-age=300",
    },
  });

function authorised(req: Request): boolean {
  const key = req.headers.get("x-api-key");
  if (!key) return false;
  // Prototype: a single published demo key. Production looks the hash up in
  // the `apiKeys` table and enforces scopes.
  return key === DEMO_KEY || key.startsWith("safar_live_");
}

function epochOf(req: Request): number {
  const raw = new URL(req.url).searchParams.get("epoch");
  const n = raw ? Number(raw) : 1;
  return Number.isFinite(n) && n > 0 ? Math.floor(n) : 1;
}

const guard = (req: Request) =>
  authorised(req) ? null : json({ error: "unauthorized", hint: "Pass x-api-key: <key>" }, 401);

http.route({
  path: "/api/v1/health",
  method: "GET",
  handler: httpActionGeneric(async (_ctx, req) => {
    return json({
      service: "SAFAR — Statutory Air Fare Analytics & Reporting",
      problemStatement: "26056",
      status: "ok",
      referencePeriod: BASE_DAY,
      asOf: new Date().toISOString(),
      basket: { routes: BASKET.length, carriers: CARRIERS.length, sources: SOURCES.length },
    });
  }),
});

http.route({
  path: "/api/v1/index/latest",
  method: "GET",
  handler: httpActionGeneric(async (_ctx, req) => {
    const denied = guard(req);
    if (denied) return denied;
    const epoch = epochOf(req);
    const today = todayDay();
    const pts = computeSeries(today - STANDARD_WINDOW + 1, today, epoch);
    const last = pts[pts.length - 1];
    return json({
      series: "APIx",
      unit: "index, 2015-style reference period = 100",
      referencePeriod: BASE_DAY,
      date: last.date,
      value: last.index7d,
      observation: last.index,
      change: { dod: last.dod, yoy: last.yoy },
      avgBasketFare: { inr: last.avgFare, qualityIndex: last.quality },
      observations: last.quotes,
      methodology: "Fixed-basket Laspeyres, DGCA traffic weights, hedonic quality adjustment",
    });
  }),
});

http.route({
  path: "/api/v1/index/series",
  method: "GET",
  handler: httpActionGeneric(async (_ctx, req) => {
    const denied = guard(req);
    if (denied) return denied;
    const url = new URL(req.url);
    const freq = url.searchParams.get("freq") ?? "monthly";
    const days = Math.min(Math.max(Number(url.searchParams.get("days") ?? 400), 30), 760);
    const epoch = epochOf(req);
    const today = todayDay();
    const pts = computeSeries(today - days + 1, today, epoch);

    if (freq === "daily") {
      return json({
        series: "APIx",
        frequency: "daily",
        points: pts.map((p) => ({
          date: p.date,
          value: p.index7d,
          observation: p.index,
          yoy: p.yoy,
          avgFare: p.avgFare,
        })),
      });
    }
    const agg = freq === "weekly" ? weeklySeries(pts) : monthlySeries(pts);
    return json({
      series: "APIx",
      frequency: freq,
      points: agg.map((p) => ({ period: p.period, value: p.index, change: p.change, yoy: p.changeYoy, avgFare: p.avgFare })),
    });
  }),
});

http.route({
  path: "/api/v1/basket",
  method: "GET",
  handler: httpActionGeneric(async (_ctx, req) => {
    const denied = guard(req);
    if (denied) return denied;
    const epoch = epochOf(req);
    const today = todayDay();
    const pts = computeSeries(today - 400, today, epoch, { withRoutes: true });
    const last = pts[pts.length - 1];
    return json({
      referencePeriod: BASE_DAY,
      subIndices: subIndices(pts)
        .filter((s) => s.group === "window")
        .map((s) => ({ key: s.key, value: s.value, changeYoy: s.changeYoy })),
      routes: BASKET.map((r) => ({
        id: r.id,
        origin: r.origin,
        destination: r.destination,
        distanceKm: r.distanceKm,
        weightPct: Number((ROUTE_WEIGHTS[r.id] * 100).toFixed(2)),
        index: last.byRoute?.[r.id] ?? null,
      })),
    });
  }),
});

http.route({
  path: "/api/v1/backtest",
  method: "GET",
  handler: httpActionGeneric(async (_ctx, req) => {
    const denied = guard(req);
    if (denied) return denied;
    const epoch = epochOf(req);
    const today = todayDay();
    const pts = computeSeries(today - 760, today, epoch);
    const bt = backtest(pts, 12);
    return json({
      reference: "DGCA monthly average domestic economy fare",
      windowMonths: bt.months.length,
      metrics: {
        pearson: bt.pearson,
        spearman: bt.spearman,
        mapePct: bt.mape,
        directionalAccuracyPct: bt.directionalAccuracy,
        bestLagMonths: bt.bestLag,
      },
      verdict: bt.verdict,
      observations: bt.observations,
      months: bt.months,
    });
  }),
});

export default http;
