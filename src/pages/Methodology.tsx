import { useQuery } from "convex/react";
import { api } from "@/convex/_generated/api";
import { Arrow, FlowNode, Label, Loading, Panel, Table, TD, TR, Tag } from "@/components/neo";

export default function Methodology() {
  const m = useQuery(api.apix.methodology);
  if (!m) return <Loading label="Loading PSI documentation" />;

  return (
    <div className="neo-in space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="neo-mono text-[10px] font-bold uppercase tracking-[0.24em] text-muted-foreground">
            Price Statistic of Prices · PSI 2026
          </p>
          <h1 className="neo-display mt-1 text-4xl md:text-5xl">Methodology</h1>
        </div>
        <div className="flex flex-wrap gap-2">
          <Tag tone="ink">Reference {m.basePeriod} = 100</Tag>
          <Tag tone="blue">{m.routes.length} city-pairs</Tag>
          <Tag tone="yellow">{m.carriers.length} carriers · {m.sources.length} sources</Tag>
        </div>
      </div>

      <Panel kicker="The estimator" title="How APIx is built" tone="ink">
        <div className="neo-2 bg-white p-4 text-center">
          <p className="neo-mono text-lg font-bold tracking-tight md:text-2xl">{m.formula}</p>
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-4">
          {[
            { k: "wᵣ — weight", v: "DGCA city-pair passenger share, fixed within the reference period" },
            { k: "Pᵣ — price", v: "Seat-share weighted economy fare on r, all taxes and UDF, booking-curve weighted across the five windows" },
            { k: "Q(d) — quality", v: "Hedonic index of the observed fare mix: legroom, meals, changeability, carbon intensity" },
            { k: "0 — base", v: "7-day mean around the reference date, the CPI's reference-period averaging" },
          ].map((x) => (
            <div key={x.k} className="neo-2 neo-shadow-sm bg-white p-3">
              <p className="neo-mono text-[10px] font-bold uppercase tracking-[0.14em]">{x.k}</p>
              <p className="mt-1 text-xs leading-5 text-muted-foreground">{x.v}</p>
            </div>
          ))}
        </div>
        <ul className="mt-4 space-y-2 text-sm leading-6">
          <li>• <strong>Fixed basket.</strong> Weights change only on the annual DGCA release, exactly like CPI spending weights.</li>
          <li>• <strong>Double quality adjustment.</strong> Median rather than mean for the route price, so one sold-out fare cannot move the index; hedonic divisor for mix shift.</li>
          <li>• <strong>Three frequencies.</strong> Daily is the headline; weekly and monthly are means of the daily series, released on the NSO calendar.</li>
          <li>• <strong>Sub-groups.</strong> Five advance-purchase windows and five DGCA regions, plus the channel split (airline direct vs OTA).</li>
          <li>• <strong>Revision policy.</strong> Provisional for 60 days, then frozen; any cleaning-rule change is versioned and re-run over the full history.</li>
        </ul>
      </Panel>

      <Panel kicker="Fixed basket" title="24 DGCA-weighted city-pairs">
        <Table head={["Route", "Region", "Distance", "Weight %", "Fare level index"]}>
          {m.routes.map((r) => (
            <TR key={r.id}>
              <TD className="font-bold">
                {r.origin} → {r.destination}
              </TD>
              <TD>{r.region}</TD>
              <TD className="text-right">{r.distanceKm} km</TD>
              <TD className="text-right">{r.weight.toFixed(2)}</TD>
              <TD className="text-right">{(r.weight / m.routes[0].weight).toFixed(2)}×</TD>
            </TR>
          ))}
        </Table>
      </Panel>

      <div className="grid gap-4 xl:grid-cols-2">
        <Panel kicker="Cell structure" title="Fare classes & hedonic attributes">
          <Table head={["Class", "Price ×", "Quality", "Legroom", "Meals", "Changeable", "CO₂ kg"]}>
            {m.fareClasses.map((f) => (
              <TR key={f.code}>
                <TD className="font-bold">{f.label}</TD>
                <TD className="text-right">{f.priceFactor.toFixed(2)}</TD>
                <TD className="text-right">{f.quality.toFixed(2)}</TD>
                <TD className="text-right">{f.legroom}"</TD>
                <TD className="text-right">{f.meals}</TD>
                <TD className="text-right">{(f.changeability * 100).toFixed(0)}%</TD>
                <TD className="text-right">{f.carbonKg.toFixed(2)}</TD>
              </TR>
            ))}
          </Table>
          <Label>Advance-purchase windows & booking-curve weights</Label>
          <Table head={["Window", "Weight in the route price"]}>
            {m.leadTimes.map((l) => (
              <TR key={l.leadTime}>
                <TD className="font-bold">T+{l.leadTime}</TD>
                <TD className="text-right">{(l.weight * 100).toFixed(0)}%</TD>
              </TR>
            ))}
          </Table>
        </Panel>

        <div className="space-y-4">
          <Panel kicker="Carriers & channels" title="Who is observed">
            <Table head={["Carrier", "Group", "Seat share", "Amenity score"]}>
              {m.carriers.map((c) => (
                <TR key={c.code}>
                  <TD className="font-bold">
                    {c.name} ({c.code})
                  </TD>
                  <TD>{c.group}</TD>
                  <TD className="text-right">{(c.seatShare * 100).toFixed(0)}%</TD>
                  <TD className="text-right">{c.amenity.toFixed(2)}</TD>
                </TR>
              ))}
            </Table>
            <Label>Distribution channels</Label>
            <div className="flex flex-wrap gap-1.5">
              {m.sources.map((s) => (
                <Tag key={s.id} tone={s.kind === "airline" ? "blue" : "violet"}>
                  {s.name} · {s.rateLimitPerMin}/min
                </Tag>
              ))}
            </div>
          </Panel>

          <Panel kicker="Governance" title="Statistical hygiene">
            <ul className="space-y-2 text-sm leading-6">
              <li>• <strong>Outliers:</strong> median ± 3 × scaled MAD per (route, window, day) cell, plus absolute sanity bounds — robust to genuine fare spikes.</li>
              <li>• <strong>Missing data:</strong> blocked or failed cells are imputed from the carrier's own fare index and flagged; imputation coverage is published with every release.</li>
              <li>• <strong>Sold-out and cancelled flights</strong> are excluded, never recorded as zero.</li>
              <li>• <strong>Tax decomposition</strong> is verified per quote: base + GST + passenger fee + UDF + convenience fee = total.</li>
              <li>• <strong>Reproducibility:</strong> the same seed yields the same 2.4 M quotes; every run is versioned and the audit trail is retained.</li>
            </ul>
          </Panel>
        </div>
      </div>

      <Panel kicker="Deployment" title="How it runs in production">
        <div className="flex flex-col gap-2 lg:flex-row lg:items-stretch">
          <FlowNode title="Scrapy cluster" sub="Dockerised, 4 workers, Playwright render for JS pages" tone="blue" className="flex-1" />
          <Arrow label="kafka" />
          <FlowNode title="Raw store" sub="Object storage · partitioned by source/date, immutable" tone="white" className="flex-1" />
          <Arrow label="clean" />
          <FlowNode title="Warehouse" sub="Postgres + TimescaleDB · dbt models for PSI cells" tone="yellow" className="flex-1" />
          <Arrow label="index" />
          <FlowNode title="Release service" sub="Daily / weekly / monthly builds with revision policy" tone="ink" className="flex-1" />
          <Arrow label="serve" />
          <FlowNode title="API + dashboard" sub="Convex realtime for the console, REST for NSO/RBI" tone="green" className="flex-1" />
        </div>
        <div className="mt-4 grid gap-2 sm:grid-cols-3">
          <div className="neo-2 bg-white p-3 text-xs leading-5">
            <strong>Scheduler.</strong> 05:00 IST sweep (all 11 sources), 06:00 clean + index, 06:30
            release, 09:00 DGCA reconciliation report.
          </div>
          <div className="neo-2 bg-white p-3 text-xs leading-5">
            <strong>Monitoring.</strong> Per-source success rate, quote yield, blocked-cell rate and
            index revision triggers. A source below 80% yield is auto-downgraded and imputed.
          </div>
          <div className="neo-2 bg-white p-3 text-xs leading-5">
            <strong>Governance.</strong> Data-sharing MoU with each source, published methodology
            note, and a public corrections log — the three things a statistical agency requires
            before adoption.
          </div>
        </div>
      </Panel>
    </div>
  );
}
