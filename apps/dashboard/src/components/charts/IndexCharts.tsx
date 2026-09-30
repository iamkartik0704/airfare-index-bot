import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { IndexPoint } from "@/api/types";
import { fixed, inr, inrCompact, monthLabel, num, shortDate } from "@/lib/format";
import { axisProps, C, ChartFrame, ChartTip, chartMargin, LegendSwatch } from "./ChartKit";

export interface SeriesToggles {
  value: boolean;
  rolling: boolean;
  nominal: boolean;
  avgFare?: boolean;
}

/** Parse API Decimal strings into chart rows. No derivation happens here. */
function rows(items: IndexPoint[]) {
  return items.map((p) => ({
    date: p.period_start,
    value: num(p.value),
    rolling: num(p.rolling_value),
    nominal: num(p.nominal_value),
    avgFare: num(p.avg_fare),
  }));
}

/** Daily APIx: quality-adjusted value, trailing mean and nominal (Laspeyres) series. */
export function IndexSeriesChart({
  items,
  show,
  height = 300,
  label,
  showBase = true,
}: {
  items: IndexPoint[];
  show: SeriesToggles;
  height?: number;
  label: string;
  showBase?: boolean;
}) {
  const data = rows(items);
  return (
    <ChartFrame
      label={label}
      height={height}
      legend={
        <>
          {show.value && <LegendSwatch color={C.blue} label="APIx (quality-adjusted)" />}
          {show.rolling && <LegendSwatch color={C.ink} label="7-day rolling" />}
          {show.nominal && <LegendSwatch color={C.red} label="Nominal (no hedonic)" dashed />}
          {show.avgFare && <LegendSwatch color={C.green} label="Avg basket fare (₹, right axis)" dashed />}
          {showBase && <LegendSwatch color={C.ink} label="Base = 100" dashed />}
        </>
      }
    >
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={chartMargin}>
          <CartesianGrid vertical={false} />
          <XAxis dataKey="date" {...axisProps} minTickGap={40} tickFormatter={shortDate} />
          <YAxis yAxisId="idx" {...axisProps} width={48} domain={["auto", "auto"]} tickFormatter={(v: number) => v.toFixed(0)} />
          {show.avgFare && (
            <YAxis yAxisId="fare" orientation="right" {...axisProps} width={56} tickFormatter={inrCompact} domain={["auto", "auto"]} />
          )}
          {showBase && <ReferenceLine yAxisId="idx" y={100} stroke={C.ink} strokeWidth={2} strokeDasharray="6 4" />}
          <Tooltip
            content={
              <ChartTip labelFmt={(l) => shortDate(String(l))} fmt={(v, name) => (name.startsWith("Avg") ? inr(v) : fixed(v, 2))} />
            }
          />
          {show.value && (
            <Line yAxisId="idx" type="monotone" dataKey="value" name="APIx" stroke={C.blue} strokeWidth={2.5} dot={false} connectNulls={false} isAnimationActive={false} />
          )}
          {show.rolling && (
            <Line yAxisId="idx" type="monotone" dataKey="rolling" name="7-day rolling" stroke={C.ink} strokeWidth={3} dot={false} isAnimationActive={false} />
          )}
          {show.nominal && (
            <Line yAxisId="idx" type="monotone" dataKey="nominal" name="Nominal" stroke={C.red} strokeWidth={2} strokeDasharray="5 4" dot={false} isAnimationActive={false} />
          )}
          {show.avgFare && (
            <Line yAxisId="fare" type="monotone" dataKey="avgFare" name="Avg basket fare" stroke={C.green} strokeWidth={2} strokeDasharray="3 3" dot={false} isAnimationActive={false} />
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </ChartFrame>
  );
}

/** Weekly / monthly APIx as bars against the base-100 line. */
export function PeriodBarChart({
  items,
  height = 240,
  label,
  frequency,
}: {
  items: IndexPoint[];
  height?: number;
  label: string;
  frequency: "WEEKLY" | "MONTHLY";
}) {
  const data = rows(items);
  const fmtLabel = (v: string) => (frequency === "MONTHLY" ? monthLabel(v) : shortDate(v));
  return (
    <ChartFrame label={label} height={height}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={chartMargin}>
          <CartesianGrid vertical={false} />
          <XAxis dataKey="date" {...axisProps} tickFormatter={fmtLabel} minTickGap={8} />
          <YAxis {...axisProps} width={48} domain={["auto", "auto"]} tickFormatter={(v: number) => v.toFixed(0)} />
          <ReferenceLine y={100} stroke={C.ink} strokeWidth={2} strokeDasharray="6 4" />
          <Tooltip cursor={{ fill: "rgba(255,212,0,0.25)" }} content={<ChartTip labelFmt={(l) => fmtLabel(String(l))} fmt={(v) => fixed(v, 2)} />} />
          <Bar dataKey="value" name="APIx" stroke={C.ink} strokeWidth={2} isAnimationActive={false}>
            {data.map((d) => (
              <Cell key={d.date} fill={(d.value ?? 100) >= 100 ? C.red : C.green} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartFrame>
  );
}
