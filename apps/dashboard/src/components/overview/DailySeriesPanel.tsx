import { useState } from "react";
import { useIndexSeries } from "@/api/queries";
import { IndexSeriesChart, type SeriesToggles } from "@/components/charts/IndexCharts";
import { OriginBadge } from "@/components/honesty";
import { Btn, Panel, Segmented } from "@/components/neo";
import { QueryState } from "@/components/states";
import { addDays } from "@/lib/format";

type Range = "30" | "90" | "365";

export function DailySeriesPanel({ latestDate }: { latestDate: string }) {
  const [range, setRange] = useState<Range>("90");
  const [show, setShow] = useState<SeriesToggles>({ value: true, rolling: true, nominal: false, avgFare: false });
  const q = useIndexSeries("daily", { start_date: addDays(latestDate, -Number(range) + 1), end_date: latestDate });
  const toggle = (k: keyof SeriesToggles) => setShow((s) => ({ ...s, [k]: !s[k] }));

  return (
    <Panel
      className="xl:col-span-2"
      kicker="Daily series"
      title="The index itself"
      right={
        <>
          <OriginBadge origin={q.data?.data_origin} />
          <Segmented
            label="Date range"
            value={range}
            onChange={setRange}
            options={[
              { value: "30", label: "30 d" },
              { value: "90", label: "90 d" },
              { value: "365", label: "1 y" },
            ]}
          />
        </>
      }
    >
      <div role="group" aria-label="Series shown" className="mb-3 flex flex-wrap gap-1.5">
        <Btn className="px-2 py-1 text-[10px]" active={show.value} onClick={() => toggle("value")}>
          APIx
        </Btn>
        <Btn className="px-2 py-1 text-[10px]" active={show.rolling} onClick={() => toggle("rolling")}>
          7-day rolling
        </Btn>
        <Btn className="px-2 py-1 text-[10px]" active={show.nominal} onClick={() => toggle("nominal")}>
          Nominal
        </Btn>
        <Btn className="px-2 py-1 text-[10px]" active={Boolean(show.avgFare)} onClick={() => toggle("avgFare")}>
          Avg fare ₹
        </Btn>
      </div>
      <QueryState query={q} loadingLabel="Loading daily series" emptyLabel="No daily index values in this range" isEmpty={(d) => d.items.length === 0}>
        {(series) => (
          <IndexSeriesChart
            items={series.items}
            show={show}
            height={300}
            label={`Daily APIx over the last ${range} days, ${series.items.length} points`}
          />
        )}
      </QueryState>
    </Panel>
  );
}
