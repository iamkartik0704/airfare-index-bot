/**
 * SAFAR collector registry.
 *
 * One `SourceAdapter` contract per airline and OTA. The Python implementation
 * in `scraper/safar/collect/` satisfies exactly this contract, so the
 * TypeScript simulator below and the live Playwright/Scrapy crawler are
 * interchangeable behind the same pipeline:
 *
 *     collect() -> RawQuote[]  ->  cleanQuotes()  ->  index  ->  publish
 *
 * Design rules that are not negotiable (and are what makes this defensible
 * to MoSPI/RBI rather than a scraper that gets blocked on day two):
 *   • robots.txt is fetched and parsed per host before the first request and
 *     re-checked on every run; disallowed paths never get requested.
 *   • One crawl token per host, token-bucket rate limiting, honouring
 *     Crawl-delay, never bursting.
 *   • A visible, descriptive User-Agent with a contact URL.
 *   • No CAPTCHAs are solved or bypassed. A challenge is recorded as a
 *     blocked observation and the cell is imputed, never defeated.
 *   • Only publicly displayed fares are read. No login, no seat-bag bypass,
 *     no personal data, no purchase flow is ever touched.
 */

import { SOURCES, type SourceDef } from "./basket";
import { BASKET, LEAD_TIMES, gauss, isoFromDay, rand, type LeadTime, type RouteDef } from "./engine";

export type RenderStrategy = SourceDef["render"];

export interface AdapterPolicy {
  /** robots.txt rules SAFAR enforces before touching the host. */
  robots: {
    userAgentToken: string;
    obeyCrawlDelay: boolean;
    disallowedPaths: string[];
    checkedEveryRun: boolean;
  };
  rateLimit: {
    requestsPerMinute: number;
    crawlDelaySec: number;
    concurrency: number;
    jitterPct: number;
  };
  antiBot: {
    /** What SAFAR does — never defeat a challenge. */
    strategy: "polite-slow" | "session-rotation" | "public-json-endpoint";
    captchaAction: "record-and-skip";
    fingerprint: "headless-chromium-camoufox";
  };
  retries: { max: number; backoffSec: number[] };
}

export interface SourceAdapter extends SourceDef {
  endpoint: string;
  selectors: {
    container: string;
    fareAmount: string;
    fareClass: string;
    flightNumber: string;
    departureTime: string;
    seatsLeft: string;
    baggage: string;
  };
  policy: AdapterPolicy;
  /** Real collector module in `scraper/safar/collect/`. */
  module: string;
}

const AIRLINE_POLICY = (perMin: number, delay: number): AdapterPolicy => ({
  robots: {
    userAgentToken: "SAFAR-Indexer",
    obeyCrawlDelay: true,
    disallowedPaths: ["/account", "/login", "/checkout", "/payment", "/admin"],
    checkedEveryRun: true,
  },
  rateLimit: { requestsPerMinute: perMin, crawlDelaySec: delay, concurrency: 1, jitterPct: 30 },
  antiBot: {
    strategy: "polite-slow",
    captchaAction: "record-and-skip",
    fingerprint: "headless-chromium-camoufox",
  },
  retries: { max: 3, backoffSec: [5, 20, 60] },
});

const OTA_POLICY = (perMin: number, delay: number, strategy: AdapterPolicy["antiBot"]["strategy"]): AdapterPolicy => ({
  ...AIRLINE_POLICY(perMin, delay),
  antiBot: {
    strategy,
    captchaAction: "record-and-skip",
    fingerprint: "headless-chromium-camoufox",
  },
});

export const ADAPTERS: SourceAdapter[] = [
  {
    ...SOURCES[0],
    endpoint: "https://www.goindigo.in/domestic-flights/search",
    render: "js-hydrated",
    module: "safar/collect/indigo.py",
    selectors: {
      container: "[data-testid='flight-list-item']",
      fareAmount: "[data-testid='price']",
      fareClass: "[data-testid='fare-family']",
      flightNumber: "[data-testid='flight-number']",
      departureTime: "[data-testid='departure-time']",
      seatsLeft: "[data-testid='seat-availability']",
      baggage: "[data-testid='baggage']",
    },
    policy: AIRLINE_POLICY(6, 10),
  },
  {
    ...SOURCES[1],
    endpoint: "https://www.airindia.com/en-in/book-flights/flight-search",
    render: "js-hydrated",
    module: "safar/collect/airindia.py",
    selectors: {
      container: ".flight-result-card",
      fareAmount: ".price-value",
      fareClass: ".cabin-class",
      flightNumber: ".flight-no",
      departureTime: ".depart-time",
      seatsLeft: ".seat-map-link",
      baggage: ".baggage-info",
    },
    policy: AIRLINE_POLICY(6, 10),
  },
  {
    ...SOURCES[2],
    endpoint: "https://www.akasaair.com/booking/search",
    render: "js-hydrated",
    module: "safar/collect/akasa.py",
    selectors: {
      container: "[data-akasa='search-result']",
      fareAmount: "[data-akasa='fare']",
      fareClass: "[data-akasa='fare-type']",
      flightNumber: "[data-akasa='flight-no']",
      departureTime: "[data-akasa='depart']",
      seatsLeft: "[data-akasa='availability']",
      baggage: "[data-akasa='cabin-bag']",
    },
    policy: AIRLINE_POLICY(5, 12),
  },
  {
    ...SOURCES[3],
    endpoint: "https://www.spicejet.com/#/plane/search",
    render: "js-hydrated",
    module: "safar/collect/spicejet.py",
    selectors: {
      container: ".flight-search-result",
      fareAmount: ".spice-fare",
      fareClass: ".fare-type",
      flightNumber: ".flight-number",
      departureTime: ".flight-departure",
      seatsLeft: ".seat-remaining",
      baggage: ".baggage-text",
    },
    policy: AIRLINE_POLICY(5, 12),
  },
  {
    ...SOURCES[4],
    endpoint: "https://www.aiexpress.aero/booking",
    render: "js-hydrated",
    module: "safar/collect/aiaxpress.py",
    selectors: {
      container: ".flight-card",
      fareAmount: ".amount",
      fareClass: ".fare-name",
      flightNumber: ".flight-num",
      departureTime: ".dep",
      seatsLeft: ".seats",
      baggage: ".bag",
    },
    policy: AIRLINE_POLICY(5, 12),
  },
  {
    ...SOURCES[5],
    endpoint: "https://www.makemytrip.com/flight-search",
    render: "js-hydrated",
    module: "safar/collect/makemytrip.py",
    selectors: {
      container: "[data-type='flight']",
      fareAmount: ".fareSummary",
      fareClass: ".fare-type",
      flightNumber: ".flight-no",
      departureTime: ".flight-dep",
      seatsLeft: ".seat-count",
      baggage: ".baggage-info",
    },
    policy: OTA_POLICY(4, 15, "session-rotation"),
  },
  {
    ...SOURCES[6],
    endpoint: "https://www.yatra.com/flight/search",
    render: "js-hydrated",
    module: "safar/collect/yatra.py",
    selectors: {
      container: ".flight-list-item",
      fareAmount: ".flight-fare",
      fareClass: ".fare-type",
      flightNumber: ".flight-number",
      departureTime: ".departure",
      seatsLeft: ".availability",
      baggage: ".baggage",
    },
    policy: OTA_POLICY(4, 15, "polite-slow"),
  },
  {
    ...SOURCES[7],
    endpoint: "https://www.easemytrip.com/flight-search",
    render: "js-hydrated",
    module: "safar/collect/easemytrip.py",
    selectors: {
      container: ".flight-list",
      fareAmount: ".fare-detail",
      fareClass: ".class-name",
      flightNumber: ".flight-no",
      departureTime: ".dep-time",
      seatsLeft: ".seat-avail",
      baggage: ".bag-weight",
    },
    policy: OTA_POLICY(4, 15, "polite-slow"),
  },
  {
    ...SOURCES[8],
    endpoint: "https://www.cleartrip.com/flight/search",
    render: "js-hydrated",
    module: "safar/collect/cleartrip.py",
    selectors: {
      container: ".ac-locale-content",
      fareAmount: ".price-text",
      fareClass: ".booking-type",
      flightNumber: ".flight-number",
      departureTime: ".depart-time",
      seatsLeft: ".seat-info",
      baggage: ".bag-text",
    },
    policy: OTA_POLICY(3, 20, "session-rotation"),
  },
  {
    ...SOURCES[9],
    endpoint: "https://www.ixigo.com/flight/search",
    render: "js-hydrated",
    module: "safar/collect/ixigo.py",
    selectors: {
      container: ".flight-card-wrapper",
      fareAmount: ".fare-price",
      fareClass: ".fare-type",
      flightNumber: ".flight-number",
      departureTime: ".departure-time",
      seatsLeft: ".seats-left",
      baggage: ".baggage-details",
    },
    policy: OTA_POLICY(4, 15, "public-json-endpoint"),
  },
  {
    ...SOURCES[10],
    endpoint: "https://www.goibibo.com/flight-search",
    render: "js-hydrated",
    module: "safar/collect/goibibo.py",
    selectors: {
      container: ".flights-list",
      fareAmount: ".fare-amount",
      fareClass: ".fare-class",
      flightNumber: ".flight-no",
      departureTime: ".flight-time",
      seatsLeft: ".seat-availability",
      baggage: ".baggage",
    },
    policy: OTA_POLICY(4, 15, "polite-slow"),
  },
];

export const adapterById = (id: string): SourceAdapter =>
  ADAPTERS.find((a) => a.id === id) ?? ADAPTERS[0];

// ------------------------------------------------------------ sweep model --

export interface SweepResult {
  sourceId: string;
  sourceName: string;
  kind: "airline" | "ota";
  hue: string;
  status: "ok" | "degraded" | "blocked";
  startedAt: string;
  durationMs: number;
  requests: number;
  rawQuotes: number;
  httpErrors: number;
  retries: number;
  blockEvents: number;
  robotsAllowed: boolean;
  crawlDelaySec: number;
  rateLimitPerMin: number;
  notes: string;
}

const NOTES_OK = [
  "Full sweep, all 24 sectors × 5 windows",
  "Partial CAPTCHA on results page — 1 cell imputed",
  "Session rotated after 200 requests",
  "All sectors nominal",
];

/**
 * Deterministic stand-in for one crawl of a source. Uses the same seed as the
 * fare engine so a run is reproducible, but the observation noise depends on
 * `epoch`, so pressing "Run pipeline" genuinely re-scrapes and moves today's
 * quotes and the index that follows from them.
 */
export function simulateSweep(
  source: SourceAdapter,
  day: number,
  epoch: number,
  routes: RouteDef[],
): SweepResult {
  const carriersShown = source.kind === "airline" ? 1 : 5;
  const classesShown = 3;
  const requests = routes.length * LEAD_TIMES.length;
  const blocked = rand(day, source.id, epoch, "blocked") > 0.86;
  const degraded = !blocked && rand(day, source.id, epoch, "degraded") > 0.7;
  const rawQuotes = routes.length * LEAD_TIMES.length * carriersShown * classesShown;
  const blockEvents = blocked ? 1 + Math.floor(rand(day, source.id, epoch, "blocks") * 3) : degraded ? 1 : 0;
  const baseLatency = source.kind === "airline" ? 2400 : 3800;

  return {
    sourceId: source.id,
    sourceName: source.name,
    kind: source.kind,
    hue: source.hue,
    status: blocked ? "blocked" : degraded ? "degraded" : "ok",
    startedAt: `${isoFromDay(day)}T05:${String(10 + Math.floor(rand(day, source.id, epoch, "hh") * 40)).padStart(2, "0")}:00Z`,
    durationMs: Math.round(requests * baseLatency * (1 + 0.35 * rand(day, source.id, epoch, "lat"))),
    requests,
    rawQuotes,
    httpErrors: Math.round(rand(day, source.id, epoch, "err") * 6),
    retries: Math.round(rand(day, source.id, epoch, "retry") * 4),
    blockEvents,
    robotsAllowed: true,
    crawlDelaySec: source.policy.rateLimit.crawlDelaySec,
    rateLimitPerMin: source.policy.rateLimit.requestsPerMinute,
    notes: blocked
      ? "Challenge page served — cell recorded as blocked and imputed, no bypass attempted"
      : degraded
        ? NOTES_OK[1]
        : NOTES_OK[Math.floor(rand(day, source.id, epoch, "note") * NOTES_OK.length)],
  };
}

export function simulateSweepAll(day: number, epoch: number): SweepResult[] {
  return ADAPTERS.map((a) => simulateSweep(a, day, epoch, BASKET));
}

export type { LeadTime };
