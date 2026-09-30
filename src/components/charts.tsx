import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";

const INK = "#0b0b0b";
const BLUE = "#2b4cff";
const RED = "#ff4a1c";
const GREEN = "#00a878";
const YELLOW = "#ffd400";
const VIOLET = "#b14eff";

function Tip({ active, payload, label, fmt }: { active?: boolean; payload?: any[]; label?: string | number; fmt?: (v: number, name: string) => string }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="neo neo-shadow-sm bg-white px-3 py-2">
      <p className="neo-mono mb-1 text-[10px] font-bold uppercase tracking-widest">{label}</p>
      {payload.map((p) => (
        <p key={p.dataKey ?? p.name} className="neo-mono text-[11px] font-bold">
          <span className="mr-2 inline-block h-2 w-2 align-middle" style={{ background: p.color ?? p.fill }} />
          {p.name}: {fmt ? fmt(p.value, p.name) : String(p.value)}
        </p>
      ))}
    </div>
  );
}

const axisProps = {
  stroke: INK,
  strokeWidth: 2,
  tickLine: true,
  tick: { fontSize: 10, fontFamily: "JetBrains Mono", fill: "#5c5747" },
} as const;

/** Headline index: smoothed daily APIx with the raw observation behind it. */
export function IndexArea({
  data,
  height = 300,
  showRaw = true,
}: {
  data: { date: string; index7d: number; index: number }[];
  height?: number;
  showRaw?: boolean;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -18 }}>
        <CartesianGrid strokeDasharray="0" vertical={false} />
        <XAxis dataKey="date" {...axisProps} minTickGap={48} />
        <YAxis {...axisProps} width={52} domain={["dataMin - 2", "dataMax + 2"]} tickFormatter={(v) => v.toFixed(0)} />
        <ReferenceLine y={100} stroke={INK} strokeWidth={2} strokeDasharray="6 4" />
        <Tooltip content={<Tip fmt={(v) => v.toFixed(2)} />} />
        <Area
          type="monotone"
          dataKey="index7d"
          name="APIx (7-day mean)"
          stroke={INK}
          strokeWidth={3}
          fill={BLUE}
          fillOpacity={0.18}
        />
        {showRaw && (
          <Area
            type="monotone"
            dataKey="index"
            name="Daily observation"
            stroke={RED}
            strokeWidth={1.5}
            strokeDasharray="4 3"
            fill="transparent"
          />
        )}
      </AreaChart>
    </ResponsiveContainer>
  );
}

/** Monthly / weekly index line, one or more series. */
export function PeriodLine({
  data,
  height = 260,
  lines = [{ key: "index", label: "APIx", color: BLUE }],
}: {
  data: { label: string; [k: string]: any }[];
  height?: number;
  lines?: { key: string; label: string; color: string }[];
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -18 }}>
        <CartesianGrid strokeDasharray="0" vertical={false} />
        <XAxis dataKey="label" {...axisProps} minTickGap={24} />
        <YAxis {...axisProps} width={52} domain={["dataMin - 2", "dataMax + 2"]} tickFormatter={(v) => v.toFixed(0)} />
        <ReferenceLine y={100} stroke={INK} strokeWidth={2} strokeDasharray="6 4" />
        <Tooltip content={<Tip fmt={(v) => v.toFixed(2)} />} />
        {lines.map((l, i) => (
          <Line
            key={l.key}
            type="monotone"
            dataKey={l.key}
            name={l.label}
            stroke={l.color}
            strokeWidth={i === 0 ? 3 : 2.5}
            strokeDasharray={i === 0 ? undefined : "6 4"}
            strokeLinecap="square"
            dot={{ r: 3, fill: l.color, stroke: INK, strokeWidth: 2 }}
            activeDot={{ r: 6, fill: YELLOW, stroke: INK, strokeWidth: 2 }}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}

/** Lead-time booking curve. */
export function ElasticityLine({
  data,
  height = 260,
}: {
  data: { leadTime: number; index: number }[];
  height?: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: -18 }}>
        <CartesianGrid strokeDasharray="0" vertical={false} />
        <XAxis dataKey="leadTime" {...axisProps} tickFormatter={(v) => `T+${v}`} />
        <YAxis {...axisProps} width={62} tickFormatter={(v) => `₹${(v / 1000).toFixed(1)}k`} />
        <Tooltip
          content={
            <Tip
              fmt={(v, name) => (name === "Booking window" ? `T+${name.split(" ")[1]}` : `₹${Math.round(v)}`)}
            />
          }
        />
        <Line
          type="monotone"
          dataKey="index"
          name="Booking window"
          stroke={INK}
          strokeWidth={3}
          dot={{ r: 5, fill: YELLOW, stroke: INK, strokeWidth: 3 }}
          activeDot={{ r: 8, fill: RED, stroke: INK, strokeWidth: 3 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

/** Per-route contribution to the 30-day move, in index points. */
export function ContributionBars({
  data,
  height = 420,
}: {
  data: { routeId: string; contribution: number }[];
  height?: number;
}) {
  const sorted = [...data].sort((a, b) => a.contribution - b.contribution);
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={sorted} layout="vertical" margin={{ top: 4, right: 16, bottom: 0, left: 8 }}>
        <CartesianGrid strokeDasharray="0" horizontal={false} />
        <XAxis type="number" {...axisProps} />
        <YAxis type="category" dataKey="routeId" {...axisProps} width={82} />
        <Tooltip content={<Tip fmt={(v) => `${Number(v).toFixed(3)} pts`} />} />
        <ReferenceLine x={0} stroke={INK} strokeWidth={2} />
        <Bar dataKey="contribution" name="Contribution (index pts)" stroke={INK} strokeWidth={2}>
          {sorted.map((d) => (
            <Cell key={d.routeId} fill={d.contribution >= 0 ? RED : GREEN} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

/** Back-test: SAFAR vs the DGCA reference series, month by month. */
export function BacktestScatter({
  data,
  height = 320,
}: {
  data: { period: string; api: number; dgca: number }[];
  height?: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <ScatterChart margin={{ top: 12, right: 16, bottom: 8, left: -10 }}>
        <CartesianGrid strokeDasharray="0" />
        <XAxis
          type="number"
          dataKey="api"
          name="SAFAR APIx"
          {...axisProps}
          label={{ value: "SAFAR APIx", position: "insideBottom", offset: -4, fontSize: 11 }}
        />
        <YAxis
          type="number"
          dataKey="dgca"
          name="DGCA"
          {...axisProps}
          width={56}
          label={{ value: "DGCA", angle: -90, position: "insideLeft", fontSize: 11 }}
        />
        <ZAxis range={[70, 70]} />
        <Tooltip content={<Tip fmt={(v) => v.toFixed(1)} />} />
        <ReferenceLine
          segment={[
            { x: 96, y: 96 },
            { x: 104, y: 104 },
          ]}
          stroke={RED}
          strokeWidth={3}
        />
        <Scatter data={data} fill={BLUE} stroke={INK} strokeWidth={2} shape="square" />
      </ScatterChart>
    </ResponsiveContainer>
  );
}

/** Macro covariates over the regression window. */
export function CovariateLines({
  series,
  height = 200,
}: {
  series: { key: string; label: string; color: string; data: { date: string; value: number }[] }[];
  height?: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart margin={{ top: 8, right: 8, bottom: 0, left: -18 }}>
        <CartesianGrid strokeDasharray="0" vertical={false} />
        <XAxis dataKey="date" {...axisProps} minTickGap={40} />
        <YAxis {...axisProps} width={46} tickFormatter={(v) => v.toFixed(0)} />
        <Tooltip content={<Tip fmt={(v) => Number(v).toFixed(3)} />} />
        {series.map((s) => (
          <Line
            key={s.key}
            data={s.data}
            type="monotone"
            dataKey="value"
            name={s.label}
            stroke={s.color}
            strokeWidth={3}
            dot={false}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}

/** Small index sub-group sparkline used inside stat rows. */
export function MiniArea({
  data,
  color = BLUE,
  height = 48,
}: {
  data: { date: string; value: number }[];
  color?: string;
  height?: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 2, right: 2, bottom: 0, left: 2 }}>
        <Area
          type="monotone"
          dataKey="value"
          stroke={INK}
          strokeWidth={2}
          fill={color}
          fillOpacity={0.25}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
