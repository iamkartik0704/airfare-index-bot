import { useApi } from "@/hooks/useApi";
import { ElasticityLine } from "@/components/charts";
import { Delta, KeyVal, Label, Loading, Panel, Stat, Table, TD, TR, Tag } from "@/components/neo";

export default function LeadTime() {
  const el = useApi("elasticity");
  const subs = useApi("subIndexSeries");
  if (!el || !subs) return <Loading label="Fitting booking curve" />;

  const trough = el.points.find((p) => p.leadTime === el.optimalLead)!;
  const day1 = el.points[0];

  return (
    <div className="neo-in space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="neo-mono text-[10px] font-bold uppercase tracking-[0.24em] text-muted-foreground">
            Lead-time elasticity
          </p>
          <h1 className="neo-display mt-1 text-4xl md:text-5xl">The booking curve</h1>
        </div>
        <div className="flex flex-wrap gap-2">
          <Tag tone="yellow">Optimal window T+{el.optimalLead}</Tag>
          <Tag tone="green">Save {el.savingPct}% vs T+1</Tag>
          <Tag tone="red">Climbs {el.lateRisePct}% by T+45</Tag>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Stat label="Best window" value={`T+${el.optimalLead}`} hint={`Mean basket fare ₹${trough.index.toLocaleString("en-IN")}`} tone="yellow" />
        <Stat label="Last-minute penalty" value={`+${day1.premiumPct.toFixed(0)}%`} hint={`T+1 costs ₹${day1.index.toLocaleString("en-IN")} vs T+7`} tone="red" />
        <Stat label="Buyer saving" value={`${el.savingPct}%`} hint="Booking at the trough instead of T+1" tone="green" />
        <Stat label="Curve is not flat" value={`${el.lateRisePct}%`} hint="Fare rises again between the trough and T+45" />
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        <Panel kicker="Basket mean fare by booking window" title="Buy early, but not too early" className="xl:col-span-2">
          <ElasticityLine data={el.points} height={300} />
          <div className="mt-3">
            <Label>Window-by-window</Label>
            <Table head={["Window", "Mean fare", "vs T+7", "Elasticity", ""]}>
              {el.points.map((p) => (
                <TR key={p.leadTime}>
                  <TD className="font-bold">T+{p.leadTime}</TD>
                  <TD className="text-right">₹{p.index.toLocaleString("en-IN")}</TD>
                  <TD className="text-right">
                    <Delta value={p.premiumPct} />
                  </TD>
                  <TD className="text-right">
                    {p.leadTime === 7 ? (
                      <span className="neo-mono text-[10px] text-muted-foreground">reference</span>
                    ) : (
                      <span className="neo-mono text-xs font-bold">{p.elasticity.toFixed(3)}</span>
                    )}
                  </TD>
                  <TD className="text-right">
                    {p.leadTime === el.optimalLead ? <Tag tone="green">trough</Tag> : null}
                  </TD>
                </TR>
              ))}
            </Table>
          </div>
        </Panel>

        <div className="space-y-4">
          <Panel kicker="Interpretation" title="What the curve tells us">
            <ul className="space-y-3 text-sm leading-6">
              <li className="border-l-[6px] border-[#ff4a1c] pl-3">
                <strong>Same sector, same day, {day1.premiumPct.toFixed(0)}% apart.</strong> A
                DEL–BOM fare observed twice in one afternoon is not the same price. Manual monthly
                collection cannot see this at all.
              </li>
              <li className="border-l-[6px] border-[#00a878] pl-3">
                <strong>The trough sits at T+{el.optimalLead}.</strong> Beyond it the fare climbs{" "}
                {el.lateRisePct}% again — booking "early" is not automatically cheap.
              </li>
              <li className="border-l-[6px] border-[#2b4cff] pl-3">
                <strong>Elasticity ≈ {el.points.find((p) => p.leadTime === 15)?.elasticity.toFixed(2)}</strong>{" "}
                in the falling segment: doubling the booking window cuts the fare by roughly that
                much. It is the most consumer-relevant number the index produces.
              </li>
              <li className="border-l-[6px] border-[#ffd400] pl-3">
                <strong>For CPI:</strong> the booking window has to be fixed in the basket, or the
                index moves because travellers changed their booking behaviour, not because airfares
                changed.
              </li>
            </ul>
          </Panel>

          <Panel kicker="Sub-index history" title="T+1 vs the rest">
            <Table head={["Window", "Index", "YoY"]}>
              {subs
                .filter((s) => s.group === "window")
                .map((s) => (
                  <TR key={s.key}>
                    <TD className="font-bold">{s.key}</TD>
                    <TD className="text-right">{s.value.toFixed(1)}</TD>
                    <TD className="text-right">
                      <Delta value={s.changeYoy} />
                    </TD>
                  </TR>
                ))}
            </Table>
            <div className="mt-3">
              <KeyVal k="Booking window in basket" v="Fixed: T+1, T+7, T+15, T+30, T+45" />
              <KeyVal k="Aggregation weights" v="Observed GDS booking curve" />
              <KeyVal k="Collection per window" v="24 routes × 11 sources" />
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
}
