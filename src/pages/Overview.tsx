import { useApi } from "@/hooks/useApi";
import { IndexArea, MiniArea, PeriodLine } from "@/components/charts";
import { Delta, KeyVal, Label, Loading, Panel, Stat, Table, TD, TR, Tag } from "@/components/neo";

export default function Overview() {
  const headline = useApi("headline");
  const daily = useApi("dailySeries");
  const monthly = useApi("periodicSeries");
  const subs = useApi("subIndexSeries");
  const pipeline = useApi("pipelineState");

  if (!headline || !daily || !monthly || !subs) return <Loading />;

  const topRoutes = headline.routeRows.slice(0, 8);
  const month = monthly[monthly.length - 1];
  const prevMonth = monthly[monthly.length - 2];
  const subsSorted = [...subs].sort((a, b) => b.changeYoy - a.changeYoy);

  return (
    <div className="neo-in space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="neo-mono text-[10px] font-bold uppercase tracking-[0.24em] text-muted-foreground">
            Real-time airfare price index · daily release
          </p>
          <h1 className="neo-display mt-1 text-4xl md:text-5xl">
            Consumer airfare, <span className="text-[#2b4cff]">measured daily</span>
          </h1>
        </div>
        <div className="flex flex-wrap gap-2">
          <Tag tone="ink">Reference {headline.epoch > 1 ? "2025-09-20" : "2025-09-20"} = 100</Tag>
          <Tag tone="blue">{headline.sources} sources</Tag>
          <Tag tone="yellow">{headline.routes} city-pairs × {headline.windows} windows</Tag>
          <Tag tone="green">{headline.quotesPerSweep.toLocaleString("en-IN")} quotes/day</Tag>
          {headline.dataOrigin === "simulated" && <Tag tone="red">Simulated data</Tag>}
          {headline.dataOrigin === "mixed" && <Tag tone="yellow">Mixed data</Tag>}
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Stat
          label="APIx · 7-day mean"
          value={headline.index.toFixed(2)}
          delta={headline.momPct}
          hint={`Reference period 2025-09-20 = 100 · today's observation ${headline.rawToday.toFixed(1)}`}
          tone="blue"
        />
        <Stat
          label="Year-on-year"
          value={`${headline.yoy >= 0 ? "+" : ""}${headline.yoy.toFixed(2)}%`}
          hint="Quality-adjusted, 12-month comparison"
        />
        <Stat
          label="Basket fare (all-in)"
          value={`₹${headline.avgFare.toLocaleString("en-IN")}`}
          hint="24-city-pair weighted mean, economy, taxes included"
        />
        <Stat
          label="Last collection"
          value={pipeline?.totals.rawQuotes.toLocaleString("en-IN") ?? "—"}
          unit="quotes"
          hint={headline.lastRunAt ? `Epoch ${headline.epoch} · ${new Date(headline.lastRunAt).toLocaleTimeString("en-IN")}` : "Deterministic seed · press Run pipeline"}
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        <Panel
          className="xl:col-span-2"
          kicker="Daily series · 400 days"
          title="The index itself"
          right={
            <div className="flex gap-2">
              <Tag tone="blue">Solid = 7-day mean</Tag>
              <Tag tone="red">Dashed = raw day</Tag>
              {headline.dataOrigin !== "live" && <Tag tone="red">Simulated data</Tag>}
            </div>
          }
        >
          <IndexArea data={daily} height={320} />
          <div className="mt-3 grid gap-2 sm:grid-cols-4">
            <KeyVal k="Month" v={`${month.label} · ${month.index.toFixed(2)}`} />
            <KeyVal k="Month-on-month" v={`${prevMonth ? (((month.index - prevMonth.index) / prevMonth.index) * 100).toFixed(2) : "—"}%`} />
            <KeyVal k="Week-on-week" v={`${headline.wow >= 0 ? "+" : ""}${headline.wow.toFixed(2)}%`} />
            <KeyVal k="Day-on-day" v={`${headline.dod >= 0 ? "+" : ""}${headline.dod.toFixed(3)}%`} />
          </div>
        </Panel>

        <Panel kicker="CPI sub-groups" title="Where the move is">
          <Label>Advance-purchase windows</Label>
          <div className="space-y-2">
            {subs
              .filter((s) => s.group === "window")
              .map((s) => (
                <div key={s.key} className="neo-2 bg-white p-2">
                  <div className="flex items-center justify-between gap-2">
                    <span className="neo-mono text-[11px] font-bold">{s.label.replace("Advance purchase · ", "")}</span>
                    <span className="flex items-center gap-1.5">
                      <span className="neo-mono text-[11px] font-bold">{s.value.toFixed(1)}</span>
                      <Delta value={s.changeYoy} />
                    </span>
                  </div>
                  <MiniArea
                    data={s.series.slice(-60).map((p) => ({ date: p.date, value: p.value }))}
                    color={s.changeYoy >= 0 ? "#ff4a1c" : "#00a878"}
                    height={34}
                  />
                </div>
              ))}
          </div>
          <Label>Regions</Label>
          <Table head={["Region", "Index", "YoY"]}>
            {subs
              .filter((s) => s.group === "region")
              .map((s) => (
                <TR key={s.key}>
                  <TD>{s.key}</TD>
                  <TD className="text-right">{s.value.toFixed(1)}</TD>
                  <TD className="text-right">
                    <Delta value={s.changeYoy} />
                  </TD>
                </TR>
              ))}
          </Table>
        </Panel>
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        <Panel kicker="Monthly sub-index" title="What the NSO would print" className="xl:col-span-2" right={
            <div className="flex gap-2">
              {headline.dataOrigin !== "live" && <Tag tone="red">Simulated data</Tag>}
            </div>
          }>
          <PeriodLine data={monthly.slice(-18)} height={250} />
        </Panel>

        <Panel kicker="Fixed basket" title="Heaviest city-pairs">
          <Table head={["Route", "Wt %", "Fare", "vs base"]}>
            {topRoutes.map((r) => (
              <TR key={r.id}>
                <TD className="font-bold">
                  {r.origin} → {r.destination}
                </TD>
                <TD className="text-right">{r.weight.toFixed(2)}</TD>
                <TD className="text-right">₹{r.fare.toLocaleString("en-IN")}</TD>
                <TD className="text-right">
                  <Delta value={r.change} />
                </TD>
              </TR>
            ))}
          </Table>
          <p className="neo-mono mt-3 text-[10px] leading-4 text-muted-foreground">
            Weights are DGCA city-pair passenger shares, fixed for the reference period — the same
            rule the CPI uses for its spending weights. Weights change only when the basket is
            refreshed on the annual DGCA release.
          </p>
        </Panel>
      </div>

      <Panel kicker="Sub-group ranking" title="12-month change, all sub-groups">
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
          {subsSorted.map((s, i) => (
            <div key={s.key} className="neo-2 neo-shadow-xs bg-white p-3">
              <p className="neo-mono text-[9.5px] font-bold uppercase tracking-[0.14em] text-muted-foreground">
                {i + 1}. {s.key}
              </p>
              <p className="neo-display mt-1 text-2xl">{s.value.toFixed(1)}</p>
              <div className="mt-1">
                <Delta value={s.changeYoy} />
              </div>
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}
