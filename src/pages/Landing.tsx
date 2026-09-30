import { Link } from "react-router";
import { ArrowRight, Plane, ShieldCheck, Sparkles } from "lucide-react";
import { Arrow, FlowNode, Tag } from "@/components/neo";

const STATS = [
  { k: "24", v: "DGCA-weighted city-pairs", s: "North, South, East, West, Central corridors" },
  { k: "11", v: "live sources", s: "5 airlines · 6 OTAs, every fare class, every window" },
  { k: "5", v: "advance-purchase windows", s: "T+1 · T+7 · T+15 · T+30 · T+45" },
  { k: "~14k", v: "quotes collected per day", s: "2.4 million observations a quarter" },
];

const PROBLEMS = [
  {
    t: "90% of tickets are online",
    d: "Manual price collection at ticketing counters no longer sees the market Indian travellers actually buy from.",
  },
  {
    t: "200–400% intraday swing",
    d: "The same sector can cost 4× more tomorrow. A monthly manual survey structurally cannot observe that.",
  },
  {
    t: "CPI is blind to it",
    d: "Transport & Communication is a mandated CPI sub-group, yet air travel — a volatile, high-weight spend — is measured thinly.",
  },
];

const LAYERS = [
  { t: "Sources", s: "IndiGo · Air India · Akasa · SpiceJet · AI Express + MakeMyTrip, Yatra, EaseMyTrip, Cleartrip, ixigo, Goibibo", tone: "blue" as const },
  { t: "Governance", s: "robots.txt parsed per host · token-bucket rate limiting · no CAPTCHA bypass · public fares only", tone: "red" as const },
  { t: "Collection", s: "Playwright render for JS pages, session rotation, structured raw store, immutable audit trail", tone: "white" as const },
  { t: "Cleaning", s: "Currency parsing · de-duplication · MAD outlier rejection · sold-out handling · flagged imputation", tone: "yellow" as const },
  { t: "PSI cells", s: "24 routes × 5 windows × fare classes, typed, versioned, DGCA-weighted", tone: "white" as const },
  { t: "Index engine", s: "Fixed-basket Laspeyres · hedonic quality divisor · sub-groups · contributions", tone: "ink" as const },
  { t: "Delivery", s: "Daily / weekly / monthly releases · REST API for NSO & RBI · realtime console", tone: "green" as const },
];

export default function Landing() {
  return (
    <div className="min-h-screen bg-background">
      {/* top bar */}
      <header className="neo flex items-center justify-between border-x-0 border-t-0 bg-white px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center bg-[#0b0b0b] text-[#ffd400]">
            <Plane className="h-4 w-4" />
          </span>
          <div className="leading-none">
            <p className="neo-display text-lg">SAFAR</p>
            <p className="neo-mono text-[9px] uppercase tracking-[0.18em] text-muted-foreground">
              Statutory Air Fare Analytics &amp; Reporting
            </p>
          </div>
        </div>
        <div className="hidden items-center gap-2 md:flex">
          <Tag tone="ink">Problem statement 26056</Tag>
          <Tag tone="blue">MoSPI · DIID</Tag>
          <Tag tone="yellow">SIH 2026</Tag>
        </div>
        <Link
          to="/auth"
          className="neo-2 neo-shadow-xs neo-press flex items-center gap-2 bg-[#ffd400] px-3 py-1.5 text-xs font-bold uppercase tracking-[0.1em]"
        >
          Open console <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      </header>

      {/* hero */}
      <section className="neo-grid neo border-x-0 border-t-0 px-4 py-12 md:px-10 md:py-16">
        <div className="mx-auto max-w-6xl">
          <div className="flex flex-wrap items-center gap-2">
            <Tag tone="ink">Real-time airfare price index for India</Tag>
            <Tag tone="red">Built to augment the CPI</Tag>
          </div>
          <h1 className="neo-display mt-5 text-5xl leading-[0.9] md:text-8xl">
            The price of a flight,
            <br />
            <span className="bg-[#ffd400] px-2">measured</span>{" "}
            <span className="bg-[#2b4cff] px-2 text-white">every day.</span>
          </h1>
          <p className="mt-6 max-w-3xl text-base leading-7 md:text-lg">
            India's Consumer Price Index measures air travel through manual collection at a handful
            of outlets, in a market where over 90% of tickets are sold online and fares move{" "}
            <strong>200–400% within a day</strong>. SAFAR builds the statistic the CPI is missing: a
            fixed-basket, hedonic <strong>Airfare Price Index (APIx)</strong>, collected automatically
            from 5 airlines and 6 OTAs across 24 DGCA-weighted city-pairs and 5 advance-purchase
            windows — and releases it daily through an API the NSO and RBI can consume.
          </p>
          <div className="mt-7 flex flex-wrap gap-3">
            <Link
              to="/auth"
              className="neo neo-shadow neo-press flex items-center gap-2 bg-[#ff4a1c] px-5 py-3 text-sm font-bold uppercase tracking-[0.12em] text-white"
            >
              Launch the dashboard <ArrowRight className="h-4 w-4" />
            </Link>
            <a
              href="#architecture"
              className="neo neo-shadow neo-press flex items-center gap-2 bg-white px-5 py-3 text-sm font-bold uppercase tracking-[0.12em]"
            >
              See the architecture
            </a>
          </div>

          <div className="mt-10 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {STATS.map((s) => (
              <div key={s.k} className="neo neo-shadow-sm bg-white p-4">
                <p className="neo-display text-4xl">{s.k}</p>
                <p className="mt-1 text-xs font-bold uppercase tracking-tight">{s.v}</p>
                <p className="neo-mono mt-1 text-[10px] leading-4 text-muted-foreground">{s.s}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* problem */}
      <section className="neo border-x-0 border-t-0 bg-[#0b0b0b] px-4 py-12 text-[#f2efe6] md:px-10">
        <div className="mx-auto max-w-6xl">
          <p className="neo-mono text-[10px] font-bold uppercase tracking-[0.24em] opacity-60">
            The measurement gap
          </p>
          <h2 className="neo-display mt-2 text-4xl md:text-6xl">A CPI blind spot</h2>
          <div className="mt-8 grid gap-4 md:grid-cols-3">
            {PROBLEMS.map((p, i) => (
              <div key={p.t} className="neo border-[#f2efe6] bg-[#f2efe6] p-5 text-[#0b0b0b]">
                <p className="neo-display text-3xl text-[#ff4a1c]">0{i + 1}</p>
                <p className="neo-display mt-2 text-xl">{p.t}</p>
                <p className="mt-2 text-sm leading-6">{p.d}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* architecture */}
      <section id="architecture" className="neo-grid neo border-x-0 border-t-0 px-4 py-12 md:px-10">
        <div className="mx-auto max-w-6xl">
          <p className="neo-mono text-[10px] font-bold uppercase tracking-[0.24em] text-muted-foreground">
            System architecture
          </p>
          <h2 className="neo-display mt-2 text-4xl md:text-6xl">Seven layers, auditable end to end</h2>

          <div className="mt-8 flex flex-col gap-2 lg:flex-row lg:items-stretch">
            <FlowNode title="Sources" sub="5 airlines + 6 OTAs" tone="blue" className="flex-1" />
            <Arrow label="collect" />
            <FlowNode title="Clean" sub="Parse · dedupe · outliers · impute" tone="yellow" className="flex-1" />
            <Arrow label="aggregate" />
            <FlowNode title="Index" sub="Laspeyres + hedonic divisor" tone="ink" className="flex-1" />
            <Arrow label="publish" />
            <FlowNode title="Serve" sub="API · dashboard · ledger" tone="green" className="flex-1" />
          </div>

          <div className="mt-6 space-y-2">
            {LAYERS.map((l, i) => (
              <div key={l.t} className="flex flex-col gap-1 md:flex-row md:items-center md:gap-4">
                <span className="neo-2 neo-shadow-xs w-44 shrink-0 bg-white px-3 py-2 text-[11px] font-extrabold uppercase tracking-[0.1em]">
                  {i + 1}. {l.t}
                </span>
                <span className="neo-2 flex-1 bg-white px-3 py-2 text-xs leading-5 text-muted-foreground">
                  {l.s}
                </span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* method + compliance */}
      <section className="neo border-x-0 border-t-0 bg-white px-4 py-12 md:px-10">
        <div className="mx-auto grid max-w-6xl gap-6 lg:grid-cols-2">
          <div>
            <p className="neo-mono text-[10px] font-bold uppercase tracking-[0.24em] text-muted-foreground">
              The estimator
            </p>
            <h2 className="neo-display mt-2 text-4xl">CPI-grade, with a quality divisor</h2>
            <div className="neo neo-shadow mt-4 bg-[#0b0b0b] p-5 text-center text-[#ffd400]">
              <p className="neo-mono text-base font-bold md:text-xl">
                APIx(d) = 100 · Σᵣ wᵣ · [Pᵣ(d)/Pᵣ(0)] · [Q(0)/Q(d)]
              </p>
            </div>
            <ul className="mt-4 space-y-2 text-sm leading-6">
              <li>
                <strong>Fixed basket, fixed weights</strong> — DGCA city-pair passenger shares,
                refreshed only on the annual release.
              </li>
              <li>
                <strong>Median route price</strong> across carriers and fare classes, so one
                sold-out bucket cannot move the index.
              </li>
              <li>
                <strong>Hedonic divisor</strong> removes mix shift — a move from Saver to Flex is not
                inflation.
              </li>
              <li>
                <strong>Sub-groups</strong> by booking window, region and channel, exactly like the
                CPI's sub-group tables.
              </li>
            </ul>
          </div>

          <div>
            <p className="neo-mono text-[10px] font-bold uppercase tracking-[0.24em] text-muted-foreground">
              Ethical collection
            </p>
            <h2 className="neo-display mt-2 text-4xl">Built to be allowed back tomorrow</h2>
            <div className="mt-4 space-y-2">
              {[
                ["robots.txt is law", "Parsed per host before the first request and re-checked on every run. Disallowed paths are never requested."],
                ["Rate limits are defaults", "3–6 requests per minute per host, crawl-delay honoured, concurrency 1, jitter on every call."],
                ["CAPTCHAs are never bypassed", "A challenge is logged as a blocked observation; the cell is imputed and flagged, never defeated."],
                ["Public data only", "No login, no personal data, no seat or baggage bypass, no purchase flow ever touched."],
              ].map(([t, d]) => (
                <div key={t} className="neo-2 flex gap-3 bg-[#f2efe6] p-3">
                  <ShieldCheck className="h-4 w-4 shrink-0" />
                  <div>
                    <p className="text-xs font-extrabold uppercase">{t}</p>
                    <p className="neo-mono mt-1 text-[10px] leading-4 text-muted-foreground">{d}</p>
                  </div>
                </div>
              ))}
            </div>
            <div className="neo neo-shadow-sm mt-4 flex items-center gap-3 bg-[#ffd400] p-3">
              <Sparkles className="h-4 w-4" />
              <p className="text-xs font-bold uppercase tracking-tight">
                Back-tested against the DGCA monthly average fare — the honest benchmark, not our own output.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* impact */}
      <section className="neo-grid neo border-x-0 border-t-0 px-4 py-12 md:px-10">
        <div className="mx-auto max-w-6xl">
          <h2 className="neo-display text-4xl md:text-6xl">Why this wins</h2>
          <div className="mt-8 grid gap-3 md:grid-cols-3">
            {[
              ["Statutory by design", "Same estimator family as the CPI, same basket-and-weight discipline, same sub-group reporting — so it can be adopted, not just admired."],
              ["Consumer-facing too", "Lead-time elasticity turns a statistic into a decision: the cheapest booking window, measured, refreshed daily."],
              ["Policy-grade", "A fuel / rupee / demand decomposition tells the RBI whether an airfare spike is a supply shock or generalised inflation."],
            ].map(([t, d]) => (
              <div key={t} className="neo neo-shadow bg-white p-5">
                <p className="neo-display text-xl">{t}</p>
                <p className="mt-2 text-sm leading-6">{d}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* cta */}
      <footer className="neo border-x-0 border-b-0 bg-[#2b4cff] px-4 py-12 text-white md:px-10">
        <div className="mx-auto flex max-w-6xl flex-col items-start justify-between gap-6 md:flex-row md:items-center">
          <div>
            <p className="neo-display text-4xl md:text-6xl">Open the SAFAR console</p>
            <p className="neo-mono mt-2 max-w-xl text-[11px] uppercase leading-5 tracking-[0.12em] opacity-90">
              Live index · sector heat-map · booking curve · collector audit trail · DGCA
              back-test · API · 12-slide deck
            </p>
          </div>
          <Link
            to="/auth"
            className="neo neo-shadow neo-press flex items-center gap-2 bg-[#ffd400] px-6 py-4 text-sm font-bold uppercase tracking-[0.12em] text-[#0b0b0b]"
          >
            Get started <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
        <p className="mx-auto mt-8 max-w-6xl border-t-2 border-white/30 pt-4 text-[10px] uppercase tracking-[0.18em] opacity-80">
          SAFAR · Problem statement 26056 · Ministry of Statistics &amp; Programme Implementation,
          DIID
        </p>
      </footer>
    </div>
  );
}
