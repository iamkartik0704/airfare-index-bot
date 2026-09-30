import { useApi } from "@/hooks/useApi";
import { BacktestScatter, PeriodLine } from "@/components/charts";
import { Delta, KeyVal, Label, Loading, Panel, Stat, Table, TD, TR, Tag } from "@/components/neo";

export default function Validation() {
  const v = useApi("validation");
  if (!v) return <Loading label="Back-testing 12 months" />;

  return (
    <div className="neo-in space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="neo-mono text-[10px] font-bold uppercase tracking-[0.24em] text-muted-foreground">
            Back-test vs DGCA
          </p>
          <h1 className="neo-display mt-1 text-4xl md:text-5xl">Validation</h1>
        </div>
        <div className="flex flex-wrap gap-2">
          <Tag tone={v.verdict.startsWith("PASS") ? "green" : "yellow"}>{v.verdict}</Tag>
          <Tag tone="ink">{v.months.length} months · {v.observations} observations</Tag>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <Stat label="Pearson r" value={v.pearson.toFixed(3)} hint="Level correlation, both series rebased" tone="blue" />
        <Stat label="Spearman ρ" value={v.spearman.toFixed(3)} hint="Rank correlation — outlier robust" />
        <Stat label="MAPE" value={`${v.mape.toFixed(2)}%`} hint="Mean absolute error on ₹ levels vs DGCA" tone="yellow" />
        <Stat label="Directional accuracy" value={`${v.directionalAccuracy}%`} hint="Share of months where both series moved the same way" tone="green" />
        <Stat label="Best lag" value={`${v.bestLag} mo`} hint="Cross-correlation peak — no lead/lag needed" />
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <Panel kicker="Rebased to 100" title="SAFAR vs DGCA monthly average fare">
          <PeriodLine
            data={v.months.map((m) => ({ label: m.period, api: m.api, dgca: m.dgca }))}
            height={280}
            lines={[
              { key: "api", label: "SAFAR APIx", color: "#2b4cff" },
              { key: "dgca", label: "DGCA reference", color: "#ff4a1c" },
            ]}
          />
          <div className="mt-2 flex gap-2">
            <Tag tone="blue">Solid = SAFAR APIx</Tag>
            <Tag tone="red">Red = DGCA reference</Tag>
          </div>
        </Panel>

        <Panel kicker="Month by month" title="Correlation & level gap">
          <BacktestScatter data={v.months} height={280} />
          <Label>Cross-correlation by lag</Label>
          <div className="flex gap-1">
            {v.crossCorr.map((c) => (
              <div
                key={c.lag}
                className={`neo-2 flex-1 p-2 text-center ${c.lag === v.bestLag ? "bg-[#ffd400]" : "bg-white"}`}
              >
                <p className="neo-mono text-[9px] uppercase tracking-[0.12em] text-muted-foreground">
                  {c.lag > 0 ? `+${c.lag}` : c.lag} mo
                </p>
                <p className="neo-mono text-xs font-bold">{c.r.toFixed(2)}</p>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      <Panel kicker="Table" title="SAFAR vs DGCA, month by month">
        <Table head={["Month", "SAFAR APIx", "DGCA index", "SAFAR fare", "DGCA fare", "Gap"]}>
          {v.months.map((m) => (
            <TR key={m.period}>
              <TD className="font-bold">{m.period}</TD>
              <TD className="text-right">{m.api.toFixed(2)}</TD>
              <TD className="text-right">{m.dgca.toFixed(2)}</TD>
              <TD className="text-right">₹{m.apiFare.toLocaleString("en-IN")}</TD>
              <TD className="text-right">₹{m.dgcaFare.toLocaleString("en-IN")}</TD>
              <TD className="text-right">
                <Delta value={m.diff} />
              </TD>
            </TR>
          ))}
        </Table>
        <div className="mt-3 grid gap-2 sm:grid-cols-3">
          <div className="neo-2 bg-white p-3">
            <KeyVal k="Mean |MoM difference|" v={`${v.meanAbsMoM.toFixed(2)} pp`} />
          </div>
          <div className="neo-2 bg-white p-3">
            <KeyVal k="Systematic level gap" v={`${v.mape.toFixed(1)}% (basket scope)`} />
          </div>
          <div className="neo-2 bg-white p-3">
            <KeyVal k="Hedge ratio" v={v.hedgeRatio.toFixed(3)} />
          </div>
        </div>
        <p className="neo-mono mt-3 text-[10px] leading-4 text-muted-foreground">
          The residual level gap is structural, not an error: DGCA's published average uses a wider,
          lower-yield basket than SAFAR's 24 DGCA-weighted metro city-pairs, and DGCA averages all
          booking windows while SAFAR fixes them. SAFAR matches DGCA on movement (r ={" "}
          {v.pearson.toFixed(2)}, {v.directionalAccuracy}% directional) and explains the level
          difference with a published scope factor — which is exactly what an augmentation of the
          existing statistic has to demonstrate.
        </p>
      </Panel>

      <Panel kicker="Hedonic quality adjustment" title="Buying a better seat is not inflation">
        <div className="grid gap-4 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <PeriodLine
              data={v.qualitySeries
                .filter((_, i) => i % 3 === 0)
                .map((p) => ({ label: p.date.slice(5), nominal: p.nominal, real: p.real }))}
              height={260}
              lines={[
                { key: "nominal", label: "Nominal", color: "#ff4a1c" },
                { key: "real", label: "Quality-adjusted", color: "#2b4cff" },
              ]}
            />
            <div className="mt-2 flex gap-2">
              <Tag tone="red">Nominal (unadjusted)</Tag>
              <Tag tone="blue">Quality-adjusted APIx</Tag>
            </div>
          </div>
          <div className="neo-dotted flex flex-col justify-center border-[3px] border-dashed border-[#0b0b0b]/40 p-4">
            <p className="neo-mono text-[10px] font-bold uppercase tracking-[0.18em] text-muted-foreground">
              Why the divisor matters
            </p>
            <p className="mt-2 text-sm leading-6">
              A traveller moving from Saver to Flex raises the average fare without the cost of
              flying changing at all. SAFAR divides the price index by the hedonic quality index of
              the observed mix (legroom, meals, changeability, carbon), so the published number
              answers <em>"what would this basket have cost last year"</em> rather than{" "}
              <em>"what did people happen to buy"</em>.
            </p>
            <p className="neo-display mt-3 text-3xl">Q(d)/Q(0) = {v.hedgeRatio.toFixed(3)}</p>
          </div>
        </div>
      </Panel>
    </div>
  );
}
