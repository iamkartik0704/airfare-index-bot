import {
  Bar,
  BarChart,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { BacktestPoint, HealthBucket, LeadTimePoint } from "@/api/types";
import { dateTime, fixed, inr, inrCompact, monthLabel, num, shortDate, windowLabel } from "@/lib/format";
import { axisProps, C, ChartFrame, ChartTip, chartMargin, LegendSwatch } from "./ChartKit";

/** Booking curve: median fare per purchase window (as returned by /analytics/lead-time). */
export function LeadTimeChart({
  points,
  cheapestWindow,
  height = 280,
  label,
}: {
  points: LeadTimePoint[];
  cheapestWindow: number | null;
  height?: number;
  label: string;
}) {
  const data = points.map((p) => ({ w: windowLabel(p.purchase_window), window: p.purchase_window, fare: num(p.fare), premium: num(p.premium_pct) }));
  return (
    <ChartFrame
      label={label}
      height={height}
      legend={
        <>
          <LegendSwatch color={C.ink} label="Fare (₹)" />
          <LegendSwatch color={C.violet} label="Premium % (right axis)" dashed />
        </>
      }
    >
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ ...chartMargin, right: 4 }}>
          <CartesianGrid vertical={false} />
          <XAxis dataKey="w" {...axisProps} />
          <YAxis yAxisId="fare" {...axisProps} width={56} tickFormatter={inrCompact} domain={["auto", "auto"]} />
          <YAxis yAxisId="pct" orientation="right" {...axisProps} width={44} tickFormatter={(v: number) => `${v.toFixed(0)}%`} />
          <Tooltip content={<ChartTip fmt={(v, name) => (name === "Fare" ? inr(v) : `${fixed(v, 1)}%`)} />} />
          <Bar yAxisId="pct" dataKey="premium" name="Premium" fill={C.violet} fillOpacity={0.35} stroke={C.ink} strokeWidth={1.5} isAnimationActive={false} />
          <Line
            yAxisId="fare"
            type="monotone"
            dataKey="fare"
            name="Fare"
            stroke={C.ink}
            strokeWidth={3}
            isAnimationActive={false}
            dot={(props: { cx?: number; cy?: number; payload?: { window: number }; index?: number }) => {
              const cheapest = props.payload?.window === cheapestWindow;
              return (
                <rect
                  key={`dot-${props.index}`}
                  x={(props.cx ?? 0) - (cheapest ? 7 : 5)}
                  y={(props.cy ?? 0) - (cheapest ? 7 : 5)}
                  width={cheapest ? 14 : 10}
                  height={cheapest ? 14 : 10}
                  fill={cheapest ? C.green : C.yellow}
                  stroke={C.ink}
                  strokeWidth={2.5}
                />
              );
            }}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </ChartFrame>
  );
}

/** Back-test: APIx average fare vs benchmark average fare, with absolute % error bars. */
export function BacktestChart({
  points,
  granularity,
  benchmarkLabel,
  height = 300,
}: {
  points: BacktestPoint[];
  granularity: "DAY" | "MONTH";
  benchmarkLabel: string;
  height?: number;
}) {
  const data = points.map((p) => ({
    period: p.period,
    apix: num(p.apix_avg_fare),
    bench: num(p.benchmark_avg_fare),
    err: num(p.abs_pct_error),
  }));
  const fmtX = (v: string) => (granularity === "MONTH" ? monthLabel(v) : shortDate(v));
  return (
    <ChartFrame
      label={`APIx average fare versus ${benchmarkLabel}, ${granularity === "MONTH" ? "monthly" : "daily"}, with absolute percentage error`}
      height={height}
      legend={
        <>
          <LegendSwatch color={C.blue} label="APIx avg fare" />
          <LegendSwatch color={C.red} label={benchmarkLabel} dashed />
          <LegendSwatch color={C.yellow} label="Abs % error (right axis)" />
        </>
      }
    >
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ ...chartMargin, right: 4 }}>
          <CartesianGrid vertical={false} />
          <XAxis dataKey="period" {...axisProps} tickFormatter={fmtX} minTickGap={24} />
          <YAxis yAxisId="fare" {...axisProps} width={56} tickFormatter={inrCompact} domain={["auto", "auto"]} />
          <YAxis yAxisId="err" orientation="right" {...axisProps} width={44} tickFormatter={(v: number) => `${v.toFixed(0)}%`} />
          <Tooltip content={<ChartTip labelFmt={(l) => fmtX(String(l))} fmt={(v, name) => (name === "Abs % error" ? `${fixed(v, 2)}%` : inr(v))} />} />
          <Bar yAxisId="err" dataKey="err" name="Abs % error" fill={C.yellow} stroke={C.ink} strokeWidth={1.5} isAnimationActive={false} />
          <Line yAxisId="fare" type="monotone" dataKey="apix" name="APIx avg fare" stroke={C.blue} strokeWidth={3} dot={granularity === "MONTH"} isAnimationActive={false} />
          <Line yAxisId="fare" type="monotone" dataKey="bench" name={benchmarkLabel} stroke={C.red} strokeWidth={2.5} strokeDasharray="6 4" dot={granularity === "MONTH"} isAnimationActive={false} />
        </ComposedChart>
      </ResponsiveContainer>
    </ChartFrame>
  );
}

/** Hourly source health buckets (stacked outcomes). */
export function SourceHealthChart({ buckets, height = 220, label }: { buckets: HealthBucket[]; height?: number; label: string }) {
  const data = buckets.map((b) => ({
    t: b.bucket_start,
    ok: b.jobs_succeeded,
    failed: b.jobs_failed,
    blocked: b.blocked,
    parse: b.parse_errors,
  }));
  return (
    <ChartFrame label={label} height={height}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={chartMargin}>
          <CartesianGrid vertical={false} />
          <XAxis dataKey="t" {...axisProps} tickFormatter={(v: string) => dateTime(v)} minTickGap={40} />
          <YAxis {...axisProps} width={40} allowDecimals={false} />
          <Tooltip content={<ChartTip labelFmt={(l) => dateTime(String(l))} fmt={(v) => String(v)} />} />
          <Legend verticalAlign="bottom" height={24} iconType="square" />
          <Bar dataKey="ok" name="Succeeded" stackId="a" fill={C.green} stroke={C.ink} strokeWidth={1} isAnimationActive={false} />
          <Bar dataKey="failed" name="Failed" stackId="a" fill={C.red} stroke={C.ink} strokeWidth={1} isAnimationActive={false} />
          <Bar dataKey="blocked" name="Blocked" stackId="a" fill={C.violet} stroke={C.ink} strokeWidth={1} isAnimationActive={false} />
          <Bar dataKey="parse" name="Parse errors" stackId="a" fill={C.yellow} stroke={C.ink} strokeWidth={1} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </ChartFrame>
  );
}

/** Simple single-series index line (used for sub-index drill-downs). */
export function SimpleIndexLine({
  data,
  height = 200,
  label,
  color = C.blue,
}: {
  data: { date: string; value: number | null }[];
  height?: number;
  label: string;
  color?: string;
}) {
  return (
    <ChartFrame label={label} height={height}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={chartMargin}>
          <CartesianGrid vertical={false} />
          <XAxis dataKey="date" {...axisProps} tickFormatter={shortDate} minTickGap={40} />
          <YAxis {...axisProps} width={48} domain={["auto", "auto"]} tickFormatter={(v: number) => v.toFixed(0)} />
          <Tooltip content={<ChartTip labelFmt={(l) => shortDate(String(l))} fmt={(v) => fixed(v, 2)} />} />
          <Line type="monotone" dataKey="value" name="Index" stroke={color} strokeWidth={2.5} dot={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </ChartFrame>
  );
}
