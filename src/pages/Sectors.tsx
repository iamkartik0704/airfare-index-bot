import { useQuery } from "convex/react";
import { api } from "@/convex/_generated/api";
import { ContributionBars } from "@/components/charts";
import { Bar, Delta, Label, Loading, Panel, Table, TD, TR, Tag } from "@/components/neo";
import { cn } from "@/lib/utils";

/** Diverging scale: blue = falling fares, red = rising, magnitude by distance from zero. */
function tone(change: number): string {
  const a = Math.min(Math.abs(change) / 6, 1);
  if (change >= 0) return `rgba(255,74,28,${0.16 + a * 0.84})`;
  return `rgba(43,76,255,${0.16 + a * 0.84})`;
}

export default function Sectors() {
  const heat = useQuery(api.apix.heatmap);
  const contrib = useQuery(api.apix.routeContributions);
  const headline = useQuery(api.apix.headline);
  const channel = useQuery(api.apix.channelAnalysis);

  if (!heat || !contrib || !headline || !channel) return <Loading label="Building sector grid" />;

  const periods = [...new Set(heat.map((c) => c.period))].sort();
  const routes = headline.routeRows.map((r) => r.id);
  const cellOf = (route: string, period: string) => heat.find((c) => c.routeId === route && c.period === period);
  const maxAbs = Math.max(...contrib.map((c) => Math.abs(c.contribution)), 0.01);
  const wedgeAvg = channel.reduce((s, c) => s + c.wedgePct, 0) / channel.length;

  return (
    <div className="neo-in space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="neo-mono text-[10px] font-bold uppercase tracking-[0.24em] text-muted-foreground">
            Sector-wise analysis
          </p>
          <h1 className="neo-display mt-1 text-4xl md:text-5xl">Heat-map & contributions</h1>
        </div>
        <div className="flex flex-wrap gap-2">
          <Tag tone="red">▲ rising</Tag>
          <Tag tone="blue">▼ falling</Tag>
          <Tag tone="yellow">Distribution wedge +{wedgeAvg.toFixed(1)}%</Tag>
        </div>
      </div>

      <Panel kicker="Route × month · month-on-month %" title="Sector heat-map">
        <div className="neo-scroll overflow-x-auto pb-1">
          <div className="min-w-[820px]">
            <div
              className="grid gap-[2px]"
              style={{ gridTemplateColumns: `92px repeat(${periods.length}, minmax(0, 1fr))` }}
            >
              <div />
              {periods.map((p) => (
                <div
                  key={p}
                  className="neo-mono px-1 py-1 text-center text-[10px] font-bold uppercase tracking-wider"
                >
                  {p}
                </div>
              ))}
              {routes.map((route) => {
                const row = headline.routeRows.find((r) => r.id === route)!;
                return [
                  <div
                    key={`${route}-label`}
                    className="neo-2 flex flex-col justify-center bg-white px-2 py-1"
                  >
                    <span className="neo-mono text-[11px] font-bold leading-none">{route}</span>
                    <span className="neo-mono text-[9px] text-muted-foreground">
                      w {row.weight.toFixed(2)}%
                    </span>
                  </div>,
                  ...periods.map((p) => {
                    const c = cellOf(route, p);
                    const v = c?.change ?? 0;
                    return (
                      <div
                        key={`${route}-${p}`}
                        title={`${route} · ${p} · ${v >= 0 ? "+" : ""}${v.toFixed(2)}%`}
                        className={cn(
                          "neo-2 flex h-11 items-center justify-center text-[11px] font-bold",
                          v >= 0 ? "text-white" : "text-white",
                        )}
                        style={{ background: tone(v) }}
                      >
                        {v >= 0 ? "+" : ""}
                        {v.toFixed(1)}
                      </div>
                    );
                  }),
                ];
              })}
            </div>
          </div>
        </div>
      </Panel>

      <div className="grid gap-4 xl:grid-cols-2">
        <Panel kicker="Last 30 days" title="Contribution to the headline move">
          <ContributionBars data={contrib.map((c) => ({ routeId: c.routeId, contribution: c.contribution }))} />
          <p className="neo-mono mt-3 text-[10px] leading-4 text-muted-foreground">
            Contribution = basket weight × route price change. The five heaviest city-pairs explain
            the bulk of every move — the same concentration effect the CPI has in the transport
            sub-group.
          </p>
        </Panel>

        <Panel kicker="Decomposition" title="Every route, ranked">
          <Table head={["Route", "Weight %", "Price Δ %", "Contribution (pts)", ""]}>
            {contrib.map((c) => (
              <TR key={c.routeId}>
                <TD className="font-bold">{c.routeId}</TD>
                <TD className="text-right">{c.weight.toFixed(2)}</TD>
                <TD className="text-right">
                  <Delta value={c.priceChange} />
                </TD>
                <TD className="text-right font-bold">{c.contribution.toFixed(3)}</TD>
                <TD className="w-28">
                  <Bar
                    value={c.contribution}
                    max={maxAbs}
                    tone={c.contribution >= 0 ? "red" : "green"}
                    height={12}
                  />
                </TD>
              </TR>
            ))}
          </Table>
        </Panel>
      </div>

      <Panel kicker="Pure channel effect" title="Distribution wedge: airline direct vs OTA">
        <div className="grid gap-3 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <Label>Same seat, different checkout</Label>
            <Table head={["Route", "Airline direct", "OTA median", "Wedge ₹", "Wedge %"]}>
              {channel.slice(0, 10).map((c) => (
                <TR key={c.routeId}>
                  <TD className="font-bold">{c.routeId}</TD>
                  <TD className="text-right">₹{c.airlineDirect.toLocaleString("en-IN")}</TD>
                  <TD className="text-right">₹{c.otaMedian.toLocaleString("en-IN")}</TD>
                  <TD className="text-right font-bold">+₹{c.wedge}</TD>
                  <TD className="text-right">
                    <Delta value={c.wedgePct} />
                  </TD>
                </TR>
              ))}
            </Table>
          </div>
          <div className="neo-dotted flex flex-col justify-center border-[3px] border-dashed border-[#0b0b0b]/40 p-4">
            <p className="neo-mono text-[10px] font-bold uppercase tracking-[0.18em] text-muted-foreground">
              Why this matters for CPI
            </p>
            <p className="mt-2 text-sm leading-6">
              A large share of the "airfare" a consumer pays is a <strong>distribution cost</strong>{" "}
              — bundling, convenience fees and the OTA's margin — not a change in the cost of
              flying. Measuring the same fare on both channels and reporting the wedge separately is
              what stops channel migration from being counted as inflation.
            </p>
          </div>
        </div>
      </Panel>
    </div>
  );
}
