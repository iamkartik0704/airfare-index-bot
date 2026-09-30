import { useState } from "react";
import { useNavigate } from "react-router";
import { useHeatmap, useRoutes } from "@/api/queries";
import type { RouteSummary } from "@/api/types";
import { OriginBadge } from "@/components/honesty";
import { Bar, Delta, Field, Note, PageHeader, Panel, Segmented, Tag } from "@/components/neo";
import { Heatmap } from "@/components/sectors/Heatmap";
import { QueryState } from "@/components/states";
import { Table, TD, TR, type SortState } from "@/components/Table";
import { fixed, inr, int, num } from "@/lib/format";

type SortKey = "code" | "region" | "distance_km" | "weight_share_pct" | "latest_index" | "latest_avg_fare" | "change_mom_pct";

function sortValue(r: RouteSummary, key: SortKey): number | string {
  if (key === "code" || key === "region") return r[key];
  if (key === "distance_km") return r.distance_km;
  return num(r[key]) ?? Number.NEGATIVE_INFINITY;
}

function RouteTable({ routes }: { routes: RouteSummary[] }) {
  const navigate = useNavigate();
  const [sort, setSort] = useState<SortState>({ key: "weight_share_pct", dir: "desc" });
  const onSort = (key: string) =>
    setSort((s) => (s.key === key ? { key, dir: s.dir === "asc" ? "desc" : "asc" } : { key, dir: key === "code" || key === "region" ? "asc" : "desc" }));
  const sorted = [...routes].sort((a, b) => {
    const va = sortValue(a, sort.key as SortKey);
    const vb = sortValue(b, sort.key as SortKey);
    const cmp = typeof va === "string" ? va.localeCompare(String(vb)) : va - (vb as number);
    return sort.dir === "asc" ? cmp : -cmp;
  });
  const maxShare = Math.max(...routes.map((r) => num(r.weight_share_pct) ?? 0), 0.01);

  return (
    <Table
      caption="Basket routes, sortable"
      sort={sort}
      onSort={onSort}
      minWidth={720}
      columns={[
        { key: "code", label: "Route", sortable: true },
        { key: "region", label: "Region", sortable: true },
        { key: "distance_km", label: "Km", align: "right", sortable: true },
        { key: "weight_share_pct", label: "Weight %", align: "right", sortable: true },
        { key: "bar", label: <span className="sr-only">Weight bar</span> },
        { key: "latest_index", label: "Index", align: "right", sortable: true },
        { key: "latest_avg_fare", label: "Avg fare", align: "right", sortable: true },
        { key: "change_mom_pct", label: "MoM", align: "right", sortable: true },
      ]}
    >
      {sorted.map((r) => (
        <TR key={r.code} onClick={() => navigate(`/routes/${r.code}`)} label={`Open ${r.code} route detail`}>
          <TD className="font-bold">
            {r.origin} → {r.destination}
          </TD>
          <TD>{r.region}</TD>
          <TD align="right">{int(r.distance_km)}</TD>
          <TD align="right">{fixed(r.weight_share_pct, 2)}</TD>
          <TD className="w-24">
            <Bar value={num(r.weight_share_pct) ?? 0} max={maxShare} height={10} label={`${r.code} weight share`} />
          </TD>
          <TD align="right">{fixed(r.latest_index, 2)}</TD>
          <TD align="right">{inr(r.latest_avg_fare)}</TD>
          <TD align="right">
            <Delta value={r.change_mom_pct} />
          </TD>
        </TR>
      ))}
    </Table>
  );
}

export default function Sectors() {
  const [freq, setFreq] = useState<"WEEKLY" | "MONTHLY">("WEEKLY");
  const [periods, setPeriods] = useState(8);
  const heat = useHeatmap(freq, periods);
  const routes = useRoutes();
  const order = (routes.data ?? [])
    .slice()
    .sort((a, b) => (num(b.weight_share_pct) ?? 0) - (num(a.weight_share_pct) ?? 0))
    .map((r) => r.code);

  return (
    <div className="neo-in space-y-5">
      <PageHeader
        kicker="Sector-wise analysis"
        title="Heat-map & routes"
        right={
          <>
            <OriginBadge origin={heat.data?.data_origin} />
            <Tag tone="red">▲ rising</Tag>
            <Tag tone="blue">▼ falling</Tag>
          </>
        }
      />

      <Panel
        kicker={`Route × ${freq === "WEEKLY" ? "week" : "month"} · change vs previous period, %`}
        title="Sector heat-map"
        right={
          <>
            <Segmented
              label="Heat-map frequency"
              value={freq}
              onChange={setFreq}
              options={[
                { value: "WEEKLY", label: "Weekly" },
                { value: "MONTHLY", label: "Monthly" },
              ]}
            />
            <Field label="Periods" htmlFor="heat-periods">
              <select id="heat-periods" className="neo-input" value={periods} onChange={(e) => setPeriods(Number(e.target.value))}>
                {[4, 6, 8, 12, 26, 52].map((n) => (
                  <option key={n} value={n}>
                    {n}
                  </option>
                ))}
              </select>
            </Field>
          </>
        }
      >
        <QueryState query={heat} loadingLabel="Building sector grid" emptyLabel="No heat-map cells yet" isEmpty={(d) => !d.cells.length}>
          {(d) => <Heatmap data={d} routeOrder={order} />}
        </QueryState>
        <p className="neo-mono mt-3 text-[10px] leading-4 text-muted-foreground">
          Cell = route index change against the previous period as reported by /analytics/heatmap. Click a route for its trends and booking curve.
        </p>
      </Panel>

      <Panel kicker="Fixed basket" title="Every route" right={<Tag tone="ink">{routes.data?.length ?? "—"} city-pairs</Tag>}>
        <QueryState query={routes} loadingLabel="Loading routes" emptyLabel="No routes in the basket" isEmpty={(d) => !d.length}>
          {(r) => <RouteTable routes={r} />}
        </QueryState>
        <Note className="mt-3" title="About the weights">
          Weights are the basket weights published by the API (currently indicative domestic passenger shares, pending official PSD/DGCA
          values — see Methodology).
        </Note>
      </Panel>
    </div>
  );
}
