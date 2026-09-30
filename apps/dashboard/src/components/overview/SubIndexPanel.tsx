import { useState } from "react";
import { useIndexSeries, useSubIndices } from "@/api/queries";
import type { IndexScope, SubIndex } from "@/api/types";
import { SimpleIndexLine } from "@/components/charts/AnalyticsCharts";
import { OriginBadge } from "@/components/honesty";
import { Delta, Label, Panel } from "@/components/neo";
import { QueryState } from "@/components/states";
import { Table, TD, TR } from "@/components/Table";
import { addDays, date, fixed, inr, num } from "@/lib/format";

const WINDOW_ORDER = ["T+1", "T+7", "T+15", "T+30", "T+45"];

function SubTable({
  title,
  items,
  selected,
  onSelect,
}: {
  title: string;
  items: SubIndex[];
  selected: string | null;
  onSelect: (s: SubIndex) => void;
}) {
  return (
    <div>
      <Label>{title}</Label>
      <Table
        caption={`${title} sub-indices`}
        columns={[
          { key: "k", label: "Key" },
          { key: "v", label: "Index", align: "right" },
          { key: "c", label: "Change", align: "right" },
          { key: "f", label: "Avg fare", align: "right" },
        ]}
      >
        {items.map((s) => (
          <TR
            key={`${s.scope}-${s.scope_key}`}
            onClick={() => onSelect(s)}
            label={`Show ${s.scope_key} series`}
            className={selected === `${s.scope}:${s.scope_key}` ? "bg-yellow/40" : undefined}
          >
            <TD className="font-bold">{s.scope_key}</TD>
            <TD align="right">{fixed(s.value, 2)}</TD>
            <TD align="right">
              <Delta value={s.change_pct} />
            </TD>
            <TD align="right">{inr(s.avg_fare)}</TD>
          </TR>
        ))}
      </Table>
    </div>
  );
}

function SubSeries({ scope, scopeKey, latestDate }: { scope: IndexScope; scopeKey: string; latestDate: string }) {
  const q = useIndexSeries("daily", { scope, key: scopeKey, start_date: addDays(latestDate, -89), end_date: latestDate });
  return (
    <QueryState query={q} loadingLabel={`Loading ${scopeKey}`} emptyLabel="No series for this sub-index" isEmpty={(d) => !d.items.length}>
      {(s) => (
        <SimpleIndexLine
          label={`Daily ${scope.toLowerCase()} sub-index ${scopeKey}, last 90 days`}
          data={s.items.map((p) => ({ date: p.period_start, value: num(p.value) }))}
          height={170}
        />
      )}
    </QueryState>
  );
}

export function SubIndexPanel({ latestDate }: { latestDate: string }) {
  const q = useSubIndices();
  const [sel, setSel] = useState<{ scope: IndexScope; key: string }>({ scope: "WINDOW", key: "T+7" });
  const selectedId = `${sel.scope}:${sel.key}`;
  return (
    <Panel kicker="Sub-indices" title="Where the move is" right={<OriginBadge origin={q.data?.data_origin} />}>
      <QueryState query={q} loadingLabel="Loading sub-indices" emptyLabel="No sub-indices computed" isEmpty={(d) => !d.items.length}>
        {(d) => {
          const windows = d.items
            .filter((i) => i.scope === "WINDOW")
            .sort((a, b) => WINDOW_ORDER.indexOf(a.scope_key) - WINDOW_ORDER.indexOf(b.scope_key));
          const regions = d.items.filter((i) => i.scope === "REGION");
          const pick = (s: SubIndex) => setSel({ scope: s.scope, key: s.scope_key });
          return (
            <div className="space-y-4">
              <p className="neo-mono text-[10px] text-muted-foreground">As of {date(d.date)} · click a row for its daily series</p>
              <SubTable title="Advance-purchase windows" items={windows} selected={selectedId} onSelect={pick} />
              <SubTable title="Regions" items={regions} selected={selectedId} onSelect={pick} />
              <div>
                <Label>
                  {sel.scope} · {sel.key} · 90 days
                </Label>
                <SubSeries scope={sel.scope} scopeKey={sel.key} latestDate={latestDate} />
              </div>
            </div>
          );
        }}
      </QueryState>
    </Panel>
  );
}
