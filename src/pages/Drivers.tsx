import { useApi } from "@/hooks/useApi";
import { CovariateLines } from "@/components/charts";
import { Label, Loading, Panel, Stat, Table, TD, TR, Tag } from "@/components/neo";

export default function Drivers() {
  const dr = useApi("drivers");
  if (!dr) return <Loading label="Estimating driver model" />;

  const significant = dr.rows.filter((r) => Math.abs(r.tStat) >= 2);

  return (
    <div className="neo-in space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="neo-mono text-[10px] font-bold uppercase tracking-[0.24em] text-muted-foreground">
            Why the index moved
          </p>
          <h1 className="neo-display mt-1 text-4xl md:text-5xl">Drivers & pass-through</h1>
        </div>
        <div className="flex flex-wrap gap-2">
          <Tag tone="blue">R² {dr.r2.toFixed(2)}</Tag>
          <Tag tone="yellow">{dr.n} monthly observations</Tag>
          <Tag tone="ink">OLS with ridge, mid-month sampling</Tag>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Stat label="Model fit (R²)" value={dr.r2.toFixed(2)} hint="Share of monthly index change explained by the drivers" tone="blue" />
        <Stat
          label="Dominant driver"
          value={significant.length ? significant.sort((a, b) => Math.abs(b.tStat) - Math.abs(a.tStat))[0].name.split("(")[0].trim() : "—"}
          hint={significant.length ? `t = ${significant[0].tStat.toFixed(2)}` : "No coefficient clears |t| ≥ 2"}
          tone="yellow"
        />
        <Stat label="Fuel elasticity" value={`${dr.rows[1].coefficient.toFixed(1)}%`} hint={`t = ${dr.rows[1].tStat.toFixed(2)} · % fare change per 1% ATF`} />
        <Stat label="Observations" value={dr.n} hint="Monthly changes over the 2-year window" />
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        <Panel kicker="Δln(APIx) on monthly changes" title="Empirical decomposition" className="xl:col-span-2">
          <Table head={["Driver", "Coefficient", "t-stat", "Unit", "Reading"]}>
            {dr.rows.map((r) => (
              <TR key={r.name}>
                <TD className="font-bold">{r.name}</TD>
                <TD className="text-right">
                  <span className="neo-mono text-xs font-bold">{r.coefficient.toFixed(2)}</span>
                </TD>
                <TD className="text-right">
                  <span
                    className={`neo-2 neo-mono px-1 text-[10px] font-bold ${
                      Math.abs(r.tStat) >= 2 ? "bg-[#00a878] text-white" : "bg-[#e6e1d4]"
                    }`}
                  >
                    {r.tStat.toFixed(2)}
                  </span>
                </TD>
                <TD>{r.unit}</TD>
                <TD className="text-muted-foreground">{r.reading}</TD>
              </TR>
            ))}
          </Table>
          <p className="neo-mono mt-3 text-[10px] leading-4 text-muted-foreground">
            Coefficients are elasticities: the % change in the index for a 1% change in the driver.
            Green t-stats clear the |t| ≥ 2 significance bar at conventional levels. Fuel, rupee
            and traffic move together with the calendar, so individual elasticities are only
            partially identified — the structural pass-through below is what the fare model
            actually applies, and the regression's job is to confirm the sign and rough size.
          </p>
        </Panel>

        <Panel kicker="Engine constants" title="Structural pass-through">
          <Table head={["Channel", "Share of fare", "Note"]}>
            {dr.passThrough.map((p) => (
              <TR key={p.name}>
                <TD className="font-bold">{p.name}</TD>
                <TD className="text-right">{p.value}</TD>
                <TD className="text-muted-foreground">{p.note}</TD>
              </TR>
            ))}
          </Table>
          <div className="neo-dotted mt-4 border-[3px] border-dashed border-[#0b0b0b]/40 p-3">
            <p className="neo-mono text-[10px] font-bold uppercase tracking-[0.16em] text-muted-foreground">
              Policy read
            </p>
            <p className="mt-2 text-sm leading-6">
              With fuel at a {dr.rows[1].coefficient.toFixed(0)}% pass-through and the rupee at{" "}
              {dr.rows[2].coefficient.toFixed(0)}%, roughly a fifth of an airfare move is
              input-cost driven and roughly half is calendar and demand driven. That split is what
              lets a central bank treat an airfare spike as supply-side or demand-side rather than
              as generalised inflation.
            </p>
          </div>
        </Panel>
      </div>

      <Panel kicker="Covariate history" title="Fuel, rupee, traffic">
        <CovariateLines
          series={[
            { key: "atf", label: "Jet fuel (index)", color: "#ff4a1c", data: dr.atf },
            { key: "fx", label: "USD/INR", color: "#2b4cff", data: dr.fx },
            { key: "dem", label: "Traffic (RPK index)", color: "#00a878", data: dr.demand },
          ]}
          height={240}
        />
        <Label>Latest readings</Label>
        <div className="grid gap-2 sm:grid-cols-3">
          <div className="neo-2 bg-white p-3">
            <p className="neo-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">Jet fuel index</p>
            <p className="neo-display text-2xl">{dr.atf[dr.atf.length - 1]?.value.toFixed(3)}</p>
          </div>
          <div className="neo-2 bg-white p-3">
            <p className="neo-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">USD / INR</p>
            <p className="neo-display text-2xl">{dr.fx[dr.fx.length - 1]?.value.toFixed(2)}</p>
          </div>
          <div className="neo-2 bg-white p-3">
            <p className="neo-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">Traffic index</p>
            <p className="neo-display text-2xl">{dr.demand[dr.demand.length - 1]?.value.toFixed(3)}</p>
          </div>
        </div>
      </Panel>
    </div>
  );
}
