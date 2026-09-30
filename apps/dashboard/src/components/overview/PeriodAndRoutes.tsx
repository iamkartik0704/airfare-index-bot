import { useState } from "react";
import { Link, useNavigate } from "react-router";
import { useIndexSeries, useRoutes } from "@/api/queries";
import { PeriodBarChart } from "@/components/charts/IndexCharts";
import { OriginBadge } from "@/components/honesty";
import { Delta, Panel, Segmented } from "@/components/neo";
import { QueryState } from "@/components/states";
import { Table, TD, TR } from "@/components/Table";
import { fixed, inr, num } from "@/lib/format";

export function PeriodPanel() {
  const [freq, setFreq] = useState<"MONTHLY" | "WEEKLY">("MONTHLY");
  const q = useIndexSeries(freq === "MONTHLY" ? "monthly" : "weekly");
  return (
    <Panel
      className="xl:col-span-2"
      kicker="Period averages of the daily index"
      title={freq === "MONTHLY" ? "Monthly APIx" : "Weekly APIx"}
      right={
        <>
          <OriginBadge origin={q.data?.data_origin} />
          <Segmented
            label="Frequency"
            value={freq}
            onChange={setFreq}
            options={[
              { value: "MONTHLY", label: "Monthly" },
              { value: "WEEKLY", label: "Weekly" },
            ]}
          />
        </>
      }
    >
      <QueryState query={q} loadingLabel="Loading period series" emptyLabel="No period values yet" isEmpty={(d) => !d.items.length}>
        {(s) => (
          <PeriodBarChart
            items={s.items.slice(-18)}
            frequency={freq}
            height={250}
            label={`${freq.toLowerCase()} APIx values, red above base 100 and green below`}
          />
        )}
      </QueryState>
    </Panel>
  );
}

export function TopRoutesPanel() {
  const q = useRoutes();
  const navigate = useNavigate();
  return (
    <Panel
      kicker="Fixed basket"
      title="Heaviest city-pairs"
      right={
        <Link to="/sectors" className="neo-mono text-[10px] font-bold uppercase underline">
          All routes →
        </Link>
      }
    >
      <QueryState query={q} loadingLabel="Loading routes" emptyLabel="No routes in the basket" isEmpty={(d) => !d.length}>
        {(routes) => (
          <Table
            caption="Top routes by basket weight"
            columns={[
              { key: "r", label: "Route" },
              { key: "w", label: "Wt %", align: "right" },
              { key: "i", label: "Index", align: "right" },
              { key: "f", label: "Fare", align: "right" },
              { key: "m", label: "MoM", align: "right" },
            ]}
          >
            {[...routes]
              .sort((a, b) => (num(b.weight_share_pct) ?? 0) - (num(a.weight_share_pct) ?? 0))
              .slice(0, 8)
              .map((r) => (
                <TR key={r.code} onClick={() => navigate(`/routes/${r.code}`)} label={`Open ${r.code} route detail`}>
                  <TD className="font-bold">{r.code}</TD>
                  <TD align="right">{fixed(r.weight_share_pct, 2)}</TD>
                  <TD align="right">{fixed(r.latest_index, 2)}</TD>
                  <TD align="right">{inr(r.latest_avg_fare)}</TD>
                  <TD align="right">
                    <Delta value={r.change_mom_pct} />
                  </TD>
                </TR>
              ))}
          </Table>
        )}
      </QueryState>
    </Panel>
  );
}
