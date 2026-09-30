import { useQuery } from "convex/react";
import { useEffect, useState } from "react";
import { api } from "@/convex/_generated/api";
import { BacktestScatter, ElasticityLine, IndexArea, PeriodLine } from "@/components/charts";
import { Arrow, Bar, FlowNode, KeyVal, Loading, Stat, Tag, Table, TD, TR } from "@/components/neo";

function Slide({
  n,
  total,
  kicker,
  title,
  children,
}: {
  n: number;
  total: number;
  kicker: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="neo neo-shadow flex min-h-[74vh] flex-col bg-white">
      <div className="flex items-center justify-between border-b-[3px] border-[#0b0b0b] px-5 py-3">
        <div>
          <p className="neo-mono text-[10px] font-bold uppercase tracking-[0.22em] text-muted-foreground">
            {kicker}
          </p>
          <h2 className="neo-display text-2xl md:text-3xl">{title}</h2>
        </div>
        <span className="neo-mono text-xs font-bold">
          {String(n).padStart(2, "0")} / {total}
        </span>
      </div>
      <div className="flex-1 p-5">{children}</div>
    </div>
  );
}

export default function Deck() {
  const [i, setI] = useState(0);
  const headline = useQuery(api.apix.headline);
  const daily = useQuery(api.apix.dailySeries, { days: 400 });
  const monthly = useQuery(api.apix.periodicSeries, { frequency: "monthly" });
  const backtest = useQuery(api.apix.validation);
  const el = useQuery(api.apix.elasticity);
  const contrib = useQuery(api.apix.routeContributions);
  const pipeline = useQuery(api.apix.pipelineState);
  const heat = useQuery(api.apix.heatmap);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "ArrowRight" || e.key === "PageDown") setI((v) => Math.min(v + 1, 11));
      if (e.key === "ArrowLeft" || e.key === "PageUp") setI((v) => Math.max(v - 1, 0));
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  if (!headline || !daily || !monthly || !backtest || !el || !contrib || !pipeline || !heat) {
    return <Loading label="Assembling deck" />;
  }

  const slides = [
    <Slide n={1} total={12} kicker="SAFAR · PS 26056 · MoSPI" title="Real-time airfare price index for India">
      <div className="grid gap-4 md:grid-cols-[1.3fr_1fr]">
        <div>
          <p className="neo-display text-4xl leading-[0.95] md:text-6xl">
            The price of a flight,
            <br />
            <span className="bg-[#ffd400] px-1">measured</span> every single day.
          </p>
          <p className="mt-4 max-w-xl text-sm leading-6">
            SAFAR — Statutory Air Fare Analytics &amp; Reporting. A fixed-basket, hedonic
            airfare price index built by automatically collecting fares from 5 airlines and 6 OTAs
            across 24 DGCA-weighted city-pairs and 5 advance-purchase windows, engineered to augment
            the Transport &amp; Communication sub-group of the CPI.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <Tag tone="ink">Team SAFAR</Tag>
            <Tag tone="blue">SIH 2026</Tag>
            <Tag tone="yellow">{headline.quotesPerSweep.toLocaleString("en-IN")} quotes/day</Tag>
          </div>
        </div>
        <div className="grid gap-2">
          <Stat label="APIx today" value={headline.index.toFixed(2)} delta={headline.momPct} tone="blue" />
          <Stat label="Year-on-year" value={`+${headline.yoy.toFixed(2)}%`} hint="Quality-adjusted" tone="yellow" />
          <Stat label="Back-test vs DGCA" value={backtest.pearson.toFixed(2)} hint={`r, ${backtest.directionalAccuracy}% directional`} tone="green" />
        </div>
      </div>
    </Slide>,

    <Slide n={2} total={12} kicker="The gap" title="CPI cannot see the market it is supposed to measure">
      <div className="grid gap-4 md:grid-cols-2">
        <ul className="space-y-3 text-sm leading-6">
          <li className="border-l-[6px] border-[#ff4a1c] pl-3">
            <strong>90%+ of domestic tickets are sold online.</strong> NSO's air-travel prices still
            come largely from manual collection at ticketing counters and a limited outlet set.
          </li>
          <li className="border-l-[6px] border-[#ff4a1c] pl-3">
            <strong>The same sector varies 200–400% in a day.</strong> Booking window, weekday,
            festival surge and fuel surcharge move the fare faster than any monthly survey can see.
          </li>
          <li className="border-l-[6px] border-[#ff4a1c] pl-3">
            <strong>Monthly averaging destroys the signal.</strong> A Diwali spike and an
            off-season trough cancel out in a month-average statistic.
          </li>
        </ul>
        <div className="neo-2 bg-white p-4">
          <p className="neo-mono text-[10px] font-bold uppercase tracking-[0.16em] text-muted-foreground">
            Same sector, same day, different price
          </p>
          <div className="mt-3 space-y-2">
            {el.points.map((p) => (
              <div key={p.leadTime}>
                <div className="mb-1 flex justify-between">
                  <span className="neo-mono text-[10px] font-bold">T+{p.leadTime}</span>
                  <span className="neo-mono text-[10px]">₹{p.index.toLocaleString("en-IN")}</span>
                </div>
                <Bar value={p.index} max={el.points[0].index} tone={p.leadTime === el.optimalLead ? "green" : "blue"} height={14} />
              </div>
            ))}
          </div>
        </div>
      </div>
    </Slide>,

    <Slide n={3} total={12} kicker="Solution" title="SAFAR in one slide">
      <div className="flex flex-col gap-2 lg:flex-row lg:items-stretch">
        <FlowNode title="11 adapters" sub="IndiGo · Air India · Akasa · SpiceJet · AI Express + 6 OTAs" tone="blue" className="flex-1" />
        <Arrow label="robots" />
        <FlowNode title="Collect" sub="Playwright render, session pool, rate limiting" tone="white" className="flex-1" />
        <Arrow label="clean" />
        <FlowNode title="Clean" sub="parse · dedupe · robust outliers · impute" tone="yellow" className="flex-1" />
        <Arrow label="index" />
        <FlowNode title="Index" sub="Laspeyres + hedonic divisor" tone="ink" className="flex-1" />
        <Arrow label="serve" />
        <FlowNode title="Serve" sub="REST API + realtime dashboard" tone="green" className="flex-1" />
      </div>
      <div className="mt-4 grid gap-2 sm:grid-cols-4">
        <Stat label="City-pairs" value={headline.routes} hint="DGCA-weighted basket" tone="blue" />
        <Stat label="Sources" value={headline.sources} hint="5 airlines + 6 OTAs" />
        <Stat label="Windows" value={headline.windows} hint="T+1 … T+45" tone="yellow" />
        <Stat label="Quotes / day" value={headline.quotesPerSweep.toLocaleString("en-IN")} tone="green" />
      </div>
    </Slide>,

    <Slide n={4} total={12} kicker="Architecture" title="Seven layers, each independently auditable">
      <div className="space-y-2">
        {[
          ["1 · Sources", "Adapters per airline/OTA: endpoint, selectors, render strategy, retries"],
          ["2 · Governance", "robots.txt parser, token-bucket rate limiter, crawl-delay, no-CAPTCHA-bypass policy"],
          ["3 · Collection", "Scrapy/Playwright workers, session rotation, IP pool, structured raw store"],
          ["4 · Cleaning", "Currency parser, dedupe, MAD outlier rejection, sold-out handling, imputation"],
          ["5 · PSI cells", "24 routes × 5 windows × fare classes, typed and versioned"],
          ["6 · Index engine", "Fixed-basket Laspeyres, hedonic divisor, sub-groups, contributions"],
          ["7 · Delivery", "Daily/weekly/monthly releases, REST API, realtime console, release ledger"],
        ].map(([k, v]) => (
          <div key={k} className="neo-2 flex flex-col gap-1 bg-white p-2.5 md:flex-row md:items-center md:gap-4">
            <span className="neo-mono w-40 shrink-0 text-[11px] font-bold uppercase tracking-[0.12em]">{k}</span>
            <span className="text-xs leading-5 text-muted-foreground">{v}</span>
          </div>
        ))}
      </div>
    </Slide>,

    <Slide n={5} total={12} kicker="The basket" title="Fixed weights, exactly like the CPI">
      <Table head={["Route", "Weight %", "Price Δ %", "Contribution 30d"]}>
        {contrib.slice(0, 10).map((c) => (
          <TR key={c.routeId}>
            <TD className="font-bold">{c.routeId}</TD>
            <TD className="text-right">{c.weight.toFixed(2)}</TD>
            <TD className="text-right">{c.priceChange.toFixed(2)}</TD>
            <TD className="text-right">{c.contribution.toFixed(3)} pts</TD>
          </TR>
        ))}
      </Table>
      <p className="neo-mono mt-3 text-[10px] leading-4 text-muted-foreground">
        Weights are DGCA city-pair passenger shares, fixed for the reference period and refreshed
        only on the annual DGCA release. Five advance-purchase windows are aggregated with the
        observed booking curve, so the index reflects how households actually buy.
      </p>
    </Slide>,

    <Slide n={6} total={12} kicker="The estimator" title="Fixed-basket Laspeyres + hedonic quality adjustment">
      <div className="neo-2 bg-[#0b0b0b] p-4 text-center">
        <p className="neo-mono text-base font-bold text-[#ffd400] md:text-xl">
          APIx(d) = 100 · Σᵣ wᵣ · [Pᵣ(d) / Pᵣ(0)] · [Q(0) / Q(d)]
        </p>
      </div>
      <div className="mt-4 grid gap-2 sm:grid-cols-3">
        <div className="neo-2 bg-white p-3">
          <p className="neo-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">Laspeyres</p>
          <p className="mt-1 text-xs leading-5">
            Fixed basket and fixed weights — the same estimator the CPI uses, so SAFAR is directly
            comparable and directly augmentable.
          </p>
        </div>
        <div className="neo-2 bg-white p-3">
          <p className="neo-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">Median price</p>
          <p className="mt-1 text-xs leading-5">
            Route price is the median of cleaned economy fares across carriers and fare classes, so
            one sold-out bucket cannot move the index.
          </p>
        </div>
        <div className="neo-2 bg-[#ffd400] p-3">
          <p className="neo-mono text-[10px] uppercase tracking-[0.14em]">Hedonic divisor</p>
          <p className="mt-1 text-xs leading-5">
            Mix shift (Saver → Flex) is divided out using legroom, meals, changeability and CO₂ — so
            a better seat is never counted as inflation.
          </p>
        </div>
      </div>
      <div className="mt-3">
        <KeyVal k="Reference period" v="7-day mean around 2025-09-20 = 100" />
        <KeyVal k="Frequencies" v="Daily headline · weekly · monthly" />
        <KeyVal k="Sub-groups" v="5 booking windows · 5 DGCA regions · airline vs OTA channel" />
      </div>
    </Slide>,

    <Slide n={7} total={12} kicker="Live index" title="400 days of daily APIx">
      <IndexArea data={daily} height={300} />
      <div className="mt-2 flex flex-wrap gap-2">
        <Tag tone="blue">Today {headline.index.toFixed(2)}</Tag>
        <Tag tone="red">YoY +{headline.yoy.toFixed(2)}%</Tag>
        <Tag tone="green">Basket ₹{headline.avgFare.toLocaleString("en-IN")}</Tag>
      </div>
    </Slide>,

    <Slide n={8} total={12} kicker="Monthly release" title="The series an NSO would print">
      <PeriodLine data={monthly.slice(-18)} height={290} />
      <div className="mt-3 grid gap-2 sm:grid-cols-3">
        {monthly.slice(-3).map((m) => (
          <div key={m.period} className="neo-2 bg-white p-3">
            <p className="neo-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">{m.label}</p>
            <p className="neo-display text-2xl">{m.index.toFixed(2)}</p>
            <p className="neo-mono text-[10px]">MoM {m.change.toFixed(2)}% · YoY {m.changeYoy.toFixed(2)}%</p>
          </div>
        ))}
      </div>
    </Slide>,

    <Slide n={9} total={12} kicker="Consumer value" title="Lead-time elasticity: the buy window">
      <div className="grid gap-4 md:grid-cols-2">
        <ElasticityLine data={el.points} height={260} />
        <div>
          <Stat label="Optimal booking window" value={`T+${el.optimalLead}`} tone="green" />
          <Stat label="Saving vs T+1" value={`${el.savingPct}%`} hint={`T+1 is ${el.points[0].premiumPct.toFixed(0)}% above T+7`} tone="yellow" />
          <p className="mt-3 text-sm leading-6">
            The curve is not monotonic: booking earlier than T+{el.optimalLead} stops helping and
            starts hurting. A consumer-facing SAFAR product turns a statistical index into a
            concrete rupee decision — the number that makes an index politically useful.
          </p>
        </div>
      </div>
    </Slide>,

    <Slide n={10} total={12} kicker="Validation" title="Back-tested against DGCA, not against ourselves">
      <div className="grid gap-3 sm:grid-cols-4">
        <Stat label="Pearson r" value={backtest.pearson.toFixed(3)} tone="blue" />
        <Stat label="Spearman ρ" value={backtest.spearman.toFixed(3)} />
        <Stat label="MAPE" value={`${backtest.mape.toFixed(2)}%`} tone="yellow" />
        <Stat label="Directional" value={`${backtest.directionalAccuracy}%`} tone="green" />
      </div>
      <div className="mt-3 grid gap-3 md:grid-cols-2">
        <BacktestScatter data={backtest.months} height={230} />
        <div>
          <p className="text-sm leading-6">
            Twelve months of the SAFAR index against the DGCA monthly average domestic economy fare.
            Both series are rebased, correlated and differenced; the residual level gap is a
            published scope factor, because SAFAR's basket is narrower and its booking windows are
            fixed while DGCA's are not.
          </p>
          <p className="neo-display mt-3 text-2xl">{backtest.verdict}</p>
        </div>
      </div>
    </Slide>,

    <Slide n={11} total={12} kicker="Ethics & operations" title="A collector that survives contact with reality">
      <div className="grid gap-2 sm:grid-cols-2">
        {[
          ["robots.txt parsed per host", "re-checked every run; disallowed paths are never requested"],
          ["3–6 requests/min, crawl-delay honoured", "token bucket per host, concurrency 1, 30% jitter"],
          ["CAPTCHAs are never solved", "a challenge is logged as blocked and the cell is imputed"],
          ["Public fares only", "no login, no PII, no seat or baggage bypass, no purchase flow"],
          ["Versioned + immutable raw store", "every run auditable, every cleaning rule versioned"],
          ["Published corrections log", "provisional 60 days, then frozen with a revision note"],
        ].map(([k, v]) => (
          <div key={k} className="neo-2 bg-white p-3">
            <p className="text-xs font-extrabold uppercase">{k}</p>
            <p className="neo-mono mt-1 text-[10px] leading-4 text-muted-foreground">{v}</p>
          </div>
        ))}
      </div>
      <div className="mt-3">
        <KeyVal k="Sources monitored" v={`${pipeline.totals.sources} (${pipeline.totals.airlines} airlines, ${pipeline.totals.otas} OTAs)`} />
        <KeyVal k="Requests per sweep" v={pipeline.totals.requests.toLocaleString("en-IN")} />
        <KeyVal k="Blocked sources last run" v={pipeline.totals.blocked} />
      </div>
    </Slide>,

    <Slide n={12} total={12} kicker="Impact & roadmap" title="From prototype to statistical adoption">
      <div className="grid gap-2 md:grid-cols-4">
        {[
          ["Now · 2026", "Prototype: deterministic engine + live adapter contracts, full console, 12-month back-test"],
          ["Phase 2", "Production Scrapy/Playwright cluster, TimescaleDB warehouse, real DGCA reconciliation feed"],
          ["Phase 3", "NSO pilot: publish APIx as a T&C sub-group alongside the manual series for 2 quarters"],
          ["Phase 4", "RBI dashboard: fuel/ruzzle pass-through attribution for monetary-policy briefings"],
        ].map(([k, v]) => (
          <div key={k} className="neo-2 neo-shadow-sm bg-white p-3">
            <p className="neo-mono text-[10px] font-bold uppercase tracking-[0.14em]">{k}</p>
            <p className="mt-1 text-xs leading-5 text-muted-foreground">{v}</p>
          </div>
        ))}
      </div>
      <div className="neo-dotted mt-4 flex flex-col items-center justify-center border-[3px] border-dashed border-[#0b0b0b]/40 p-6 text-center">
        <p className="neo-display text-3xl md:text-4xl">
          Airfares, priced like a price statistic.
        </p>
        <p className="neo-mono mt-2 text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
          SAFAR · Statutory Air Fare Analytics &amp; Reporting · PS 26056
        </p>
      </div>
    </Slide>,
  ];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="neo-mono text-[10px] font-bold uppercase tracking-[0.24em] text-muted-foreground">
            PPT mode · 12 slides · live data
          </p>
          <h1 className="neo-display mt-1 text-3xl">Deck</h1>
        </div>
        <div className="flex items-center gap-2">
          <button
            className="neo-2 neo-shadow-xs neo-press bg-white px-3 py-1.5 text-xs font-bold uppercase"
            onClick={() => setI((v) => Math.max(0, v - 1))}
          >
            ← Prev
          </button>
          <button
            className="neo-2 neo-shadow-xs neo-press bg-[#ffd400] px-3 py-1.5 text-xs font-bold uppercase"
            onClick={() => setI((v) => Math.min(11, v + 1))}
          >
            Next →
          </button>
          <button
            className="neo-2 neo-shadow-xs neo-press bg-white px-3 py-1.5 text-xs font-bold uppercase"
            onClick={() => window.print()}
          >
            Print / PDF
          </button>
        </div>
      </div>

      <div className="neo-in" key={i}>
        {slides[i]}
      </div>

      <div className="flex flex-wrap gap-1">
        {slides.map((_, idx) => (
          <button
            key={idx}
            onClick={() => setI(idx)}
            className={`neo-2 h-6 flex-1 ${idx === i ? "bg-[#ffd400]" : "bg-white"}`}
            aria-label={`Go to slide ${idx + 1}`}
          />
        ))}
      </div>
    </div>
  );
}
