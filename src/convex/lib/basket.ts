/**
 * SAFAR — Statutory Air Fare Analytics & Reporting
 * PS 26056 · MoSPI (DIID)
 *
 * The fixed reference basket, carriers, distribution channels and the
 * advance-purchase windows the index is built from.
 *
 * `trafficWeight` is the DGCA domestic passenger share of the city-pair
 * (annual passengers on the sector, as a share of total domestic traffic).
 * These are SAFAR's analogue of the CPI spending weights: every route
 * contributes to the headline in proportion to how much of India's
 * domestic air travel actually happens on it.
 */

export type AirportCode = string;

export interface RouteDef {
  id: string;
  origin: AirportCode;
  destination: AirportCode;
  /** Great-circle distance, km. */
  distanceKm: number;
  /** DGCA traffic share, % of domestic passengers. Basket weights. */
  trafficWeight: number;
  /** Route-level fare level tuning (competition, stage length, LCC presence). */
  fareBias: number;
  region: "North" | "South" | "East" | "West" | "Central";
}

export const AIRPORTS: { code: AirportCode; city: string; label: string }[] = [
  { code: "DEL", city: "Delhi", label: "Indira Gandhi Intl" },
  { code: "BOM", city: "Mumbai", label: "Chhatrapati Shivaji Maharaj Intl" },
  { code: "BLR", city: "Bengaluru", label: "Kempegowda Intl" },
  { code: "CCU", city: "Kolkata", label: "Netaji Subhas Chandra Bose Intl" },
  { code: "HYD", city: "Hyderabad", label: "Rajiv Gandhi Intl" },
  { code: "MAA", city: "Chennai", label: "Chennai Intl" },
  { code: "COK", city: "Kochi", label: "Cochin Intl" },
  { code: "JAI", city: "Jaipur", label: "Jaipur Intl" },
  { code: "GOI", city: "Goa", label: "Dabolim" },
  { code: "PNQ", city: "Pune", label: "Pune Airport" },
  { code: "IXC", city: "Chandigarh", label: "Chandigarh Intl" },
  { code: "TRV", city: "Thiruvananthapuram", label: "Trivandrum Intl" },
  { code: "LKO", city: "Lucknow", label: "Chaudhary Charan Singh Intl" },
  { code: "IDR", city: "Indore", label: "Devi Ahilyabai Holkar Intl" },
  { code: "VNS", city: "Varanasi", label: "Lal Bahadur Shastri Intl" },
  { code: "PAT", city: "Patna", label: "Jay Prakash Narayan Intl" },
];

/**
 * 24 city-pairs spanning all DGCA reporting regions and both metro-tier
 * corridors. Weights are indicative FY2024 DGCA traffic shares (Indian
 * domestic passenger traffic) — the basket is refreshed on the annual DGCA
 * release and is fixed within a reference period, exactly as a CPI basket is.
 */
export const BASKET: RouteDef[] = [
  { id: "DEL-BOM", origin: "DEL", destination: "BOM", distanceKm: 1380, trafficWeight: 4.2, fareBias: 1.02, region: "West" },
  { id: "DEL-BLR", origin: "DEL", destination: "BLR", distanceKm: 1650, trafficWeight: 3.6, fareBias: 1.06, region: "South" },
  { id: "DEL-HYD", origin: "DEL", destination: "HYD", distanceKm: 1250, trafficWeight: 2.9, fareBias: 1.0, region: "South" },
  { id: "BOM-BLR", origin: "BOM", destination: "BLR", distanceKm: 850, trafficWeight: 2.4, fareBias: 1.12, region: "South" },
  { id: "DEL-CCU", origin: "DEL", destination: "CCU", distanceKm: 1480, trafficWeight: 2.1, fareBias: 0.97, region: "East" },
  { id: "BLR-HYD", origin: "BLR", destination: "HYD", distanceKm: 570, trafficWeight: 1.9, fareBias: 1.04, region: "South" },
  { id: "MAA-DEL", origin: "MAA", destination: "DEL", distanceKm: 1100, trafficWeight: 1.8, fareBias: 1.0, region: "South" },
  { id: "BLR-COK", origin: "BLR", destination: "COK", distanceKm: 1380, trafficWeight: 1.7, fareBias: 0.93, region: "South" },
  { id: "DEL-COK", origin: "DEL", destination: "COK", distanceKm: 1930, trafficWeight: 1.6, fareBias: 0.95, region: "South" },
  { id: "DEL-JAI", origin: "DEL", destination: "JAI", distanceKm: 1150, trafficWeight: 1.5, fareBias: 1.01, region: "North" },
  { id: "HYD-BOM", origin: "HYD", destination: "BOM", distanceKm: 710, trafficWeight: 1.4, fareBias: 1.09, region: "West" },
  { id: "DEL-PNQ", origin: "DEL", destination: "PNQ", distanceKm: 1270, trafficWeight: 1.3, fareBias: 1.03, region: "West" },
  { id: "DEL-TRV", origin: "DEL", destination: "TRV", distanceKm: 1750, trafficWeight: 1.1, fareBias: 0.9, region: "South" },
  { id: "CCU-BLR", origin: "CCU", destination: "BLR", distanceKm: 1400, trafficWeight: 1.1, fareBias: 0.96, region: "East" },
  { id: "DEL-IXC", origin: "DEL", destination: "IXC", distanceKm: 460, trafficWeight: 1.0, fareBias: 1.12, region: "North" },
  { id: "BLR-MAA", origin: "BLR", destination: "MAA", distanceKm: 290, trafficWeight: 1.0, fareBias: 1.22, region: "South" },
  { id: "BOM-CCU", origin: "BOM", destination: "CCU", distanceKm: 1680, trafficWeight: 1.0, fareBias: 0.94, region: "East" },
  { id: "HYD-CCU", origin: "HYD", destination: "CCU", distanceKm: 1250, trafficWeight: 0.9, fareBias: 0.92, region: "East" },
  { id: "BOM-GOI", origin: "BOM", destination: "GOI", distanceKm: 590, trafficWeight: 0.9, fareBias: 1.26, region: "West" },
  { id: "PNQ-BLR", origin: "PNQ", destination: "BLR", distanceKm: 840, trafficWeight: 0.7, fareBias: 1.05, region: "West" },
  { id: "CCU-PNQ", origin: "CCU", destination: "PNQ", distanceKm: 1180, trafficWeight: 0.6, fareBias: 0.91, region: "East" },
  { id: "DEL-VNS", origin: "DEL", destination: "VNS", distanceKm: 780, trafficWeight: 0.6, fareBias: 1.08, region: "North" },
  { id: "IDR-DEL", origin: "IDR", destination: "DEL", distanceKm: 1100, trafficWeight: 0.6, fareBias: 1.0, region: "Central" },
  { id: "DEL-LKO", origin: "DEL", destination: "LKO", distanceKm: 400, trafficWeight: 0.5, fareBias: 1.15, region: "North" },
];

export interface CarrierDef {
  code: string;
  name: string;
  group: "LCC" | "Full Service";
  /** Share of seats sold on the basket sectors. */
  seatShare: number;
  /** Average fare premium / discount vs the basket mean. */
  fareIndex: number;
  /** Weighted amenity score, 0-1. Drives the hedonic quality adjustment. */
  amenity: number;
  hue: string;
}

export const CARRIERS: CarrierDef[] = [
  { code: "6E", name: "IndiGo", group: "LCC", seatShare: 0.42, fareIndex: 0.97, amenity: 0.74, hue: "#2B59FF" },
  { code: "AI", name: "Air India", group: "Full Service", seatShare: 0.22, fareIndex: 1.14, amenity: 0.93, hue: "#FF5A36" },
  { code: "QP", name: "Akasa Air", group: "LCC", seatShare: 0.12, fareIndex: 0.9, amenity: 0.78, hue: "#FFD400" },
  { code: "SG", name: "SpiceJet", group: "LCC", seatShare: 0.11, fareIndex: 0.93, amenity: 0.71, hue: "#00A878" },
  { code: "IX", name: "Air India Express", group: "LCC", seatShare: 0.13, fareIndex: 0.88, amenity: 0.66, hue: "#B14EFF" },
];

/** Advance-purchase windows (days before departure) in the PSI basket. */
export const LEAD_TIMES = [1, 7, 15, 30, 45] as const;
export type LeadTime = (typeof LEAD_TIMES)[number];

/**
 * Observed distribution of booking windows on Indian domestic routes
 * (airline GDS booking curves). Used to collapse the five PSI cells into one
 * route-level price — the same logic as "how households actually buy".
 */
export const LEAD_TIME_WEIGHTS: Record<LeadTime, number> = {
  1: 0.08,
  7: 0.42,
  15: 0.22,
  30: 0.18,
  45: 0.1,
};

/** Fare classes and their hedonic (quality) attribute scores. */
export interface FareClassDef {
  code: string;
  label: string;
  /** Relative price level vs the economy mean. */
  priceFactor: number;
  /** Quality index, 1.0 = the reference-period economy basket. */
  quality: number;
  legroom: number;
  meals: number;
  changeability: number;
  carbonKg: number;
}

export const FARE_CLASSES: FareClassDef[] = [
  { code: "SAVER", label: "Saver / bare", priceFactor: 0.78, quality: 0.7, legroom: 30, meals: 0, changeability: 0, carbonKg: 0.17 },
  { code: "VALUE", label: "Value", priceFactor: 1.0, quality: 0.95, legroom: 32, meals: 1, changeability: 0.5, carbonKg: 0.16 },
  { code: "FLEX", label: "Flex", priceFactor: 1.34, quality: 1.22, legroom: 36, meals: 1, changeability: 1, carbonKg: 0.18 },
  { code: "PREMIUM", label: "Premium economy", priceFactor: 1.85, quality: 1.55, legroom: 38, meals: 1.4, changeability: 0.8, carbonKg: 0.22 },
  { code: "BIZ", label: "Business", priceFactor: 3.6, quality: 2.4, legroom: 44, meals: 2, changeability: 1, carbonKg: 0.31 },
];

/**
 * Distribution channels. Every fare class is observed twice: once on the
 * airline's own channel and once through an OTA. The wedge between the two is
 * the "distribution cost" SAFAR measures separately from the ticket price.
 */
export interface SourceDef {
  id: string;
  name: string;
  kind: "airline" | "ota";
  carrier?: string;
  /** Convenience / booking fee charged on top of the fare, INR. */
  convenienceFee: number;
  /** Bundled-fare discount vs the airline's own channel, fraction. */
  bundleDiscount: number;
  robotsPath: string;
  rateLimitPerMin: number;
  crawlDelaySec: number;
  /** How the source serves fares: SSR html, JS-hydrated app, or a challenge. */
  render: "static-html" | "js-hydrated" | "captcha-risk" | "json-endpoint";
  hue: string;
}

export const SOURCES: SourceDef[] = [
  { id: "indigo", name: "IndiGo (goIndiGo)", kind: "airline", carrier: "6E", convenienceFee: 0, bundleDiscount: 0, robotsPath: "/robots.txt", rateLimitPerMin: 6, crawlDelaySec: 10, render: "js-hydrated", hue: "#2B59FF" },
  { id: "airindia", name: "Air India (airindia.com)", kind: "airline", carrier: "AI", convenienceFee: 0, bundleDiscount: 0, robotsPath: "/robots.txt", rateLimitPerMin: 6, crawlDelaySec: 10, render: "js-hydrated", hue: "#FF5A36" },
  { id: "akasaair", name: "Akasa Air (akasaair.com)", kind: "airline", carrier: "QP", convenienceFee: 0, bundleDiscount: 0, robotsPath: "/robots.txt", rateLimitPerMin: 5, crawlDelaySec: 12, render: "js-hydrated", hue: "#FFD400" },
  { id: "spicejet", name: "SpiceJet (spicejet.com)", kind: "airline", carrier: "SG", convenienceFee: 0, bundleDiscount: 0, robotsPath: "/robots.txt", rateLimitPerMin: 5, crawlDelaySec: 12, render: "js-hydrated", hue: "#00A878" },
  { id: "aiaexpress", name: "Air India Express", kind: "airline", carrier: "IX", convenienceFee: 0, bundleDiscount: 0, robotsPath: "/robots.txt", rateLimitPerMin: 5, crawlDelaySec: 12, render: "js-hydrated", hue: "#B14EFF" },
  { id: "makemytrip", name: "MakeMyTrip", kind: "ota", convenienceFee: 48, bundleDiscount: 0.06, robotsPath: "/robots.txt", rateLimitPerMin: 4, crawlDelaySec: 15, render: "captcha-risk", hue: "#2B59FF" },
  { id: "yatra", name: "Yatra", kind: "ota", convenienceFee: 40, bundleDiscount: 0.05, robotsPath: "/robots.txt", rateLimitPerMin: 4, crawlDelaySec: 15, render: "js-hydrated", hue: "#FF5A36" },
  { id: "easemytrip", name: "EaseMyTrip", kind: "ota", convenienceFee: 35, bundleDiscount: 0.04, robotsPath: "/robots.txt", rateLimitPerMin: 4, crawlDelaySec: 15, render: "js-hydrated", hue: "#FFD400" },
  { id: "cleartrip", name: "Cleartrip", kind: "ota", convenienceFee: 55, bundleDiscount: 0.07, robotsPath: "/robots.txt", rateLimitPerMin: 3, crawlDelaySec: 20, render: "captcha-risk", hue: "#00A878" },
  { id: "ixigo", name: "ixigo", kind: "ota", convenienceFee: 42, bundleDiscount: 0.05, robotsPath: "/robots.txt", rateLimitPerMin: 4, crawlDelaySec: 15, render: "js-hydrated", hue: "#B14EFF" },
  { id: "goibibo", name: "MakeMyTrip / Goibibo", kind: "ota", convenienceFee: 44, bundleDiscount: 0.05, robotsPath: "/robots.txt", rateLimitPerMin: 4, crawlDelaySec: 15, render: "js-hydrated", hue: "#2B59FF" },
];

export const AIRLINE_SOURCES = SOURCES.filter((s) => s.kind === "airline");
export const OTA_SOURCES = SOURCES.filter((s) => s.kind === "ota");

/** Total basket weight (normalised to 1) per route. */
export const ROUTE_WEIGHTS: Record<string, number> = (() => {
  const total = BASKET.reduce((sum, r) => sum + r.trafficWeight, 0);
  const out: Record<string, number> = {};
  for (const r of BASKET) out[r.id] = r.trafficWeight / total;
  return out;
})();

export const routeById = (id: string): RouteDef =>
  BASKET.find((r) => r.id === id) ?? BASKET[0];

export const sourceById = (id: string): SourceDef =>
  SOURCES.find((s) => s.id === id) ?? SOURCES[0];

export const carrierByCode = (code: string): CarrierDef =>
  CARRIERS.find((c) => c.code === code) ?? CARRIERS[0];
