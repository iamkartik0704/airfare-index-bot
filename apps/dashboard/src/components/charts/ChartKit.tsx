import type { ReactNode } from "react";

/* Shared chart styling, ported from the legacy src/components/charts.tsx. */

export const C = {
  ink: "#0b0b0b",
  blue: "#2b4cff",
  red: "#ff4a1c",
  green: "#00a878",
  yellow: "#ffd400",
  violet: "#b14eff",
  muted: "#5c5747",
} as const;

export const axisProps = {
  stroke: C.ink,
  strokeWidth: 2,
  tickLine: true,
  tick: { fontSize: 10, fontFamily: "JetBrains Mono, monospace", fill: C.muted },
} as const;

export const chartMargin = { top: 8, right: 12, bottom: 0, left: 0 };

interface TipItem {
  name?: string | number;
  value?: unknown;
  color?: string;
  fill?: string;
  stroke?: string;
  dataKey?: unknown;
}

/** Neo tooltip. Recharts injects active/payload/label when cloning it. */
export function ChartTip({
  active,
  payload,
  label,
  fmt,
  labelFmt,
}: {
  active?: boolean;
  payload?: ReadonlyArray<TipItem>;
  label?: string | number;
  fmt?: (v: number, name: string) => string;
  labelFmt?: (label: string | number) => string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="neo neo-shadow-sm bg-white px-3 py-2">
      <p className="neo-mono mb-1 text-[10px] font-bold uppercase tracking-widest">
        {label !== undefined ? (labelFmt ? labelFmt(label) : label) : ""}
      </p>
      {payload.map((p, i) => {
        const n = Number(p.value);
        const name = String(p.name ?? "");
        return (
          <p key={`${name}-${i}`} className="neo-mono text-[11px] font-bold">
            <span
              className="mr-2 inline-block h-2 w-2 border border-ink align-middle"
              style={{ background: p.color ?? p.stroke ?? p.fill }}
            />
            {name}: {p.value === null || p.value === undefined ? "—" : fmt ? fmt(n, name) : String(p.value)}
          </p>
        );
      })}
    </div>
  );
}

/**
 * Accessible wrapper: charts are exposed as images with a text description;
 * the underlying numbers are always also available in a table on the page.
 */
export function ChartFrame({
  label,
  height,
  children,
  legend,
}: {
  label: string;
  height: number;
  children: ReactNode;
  legend?: ReactNode;
}) {
  return (
    <figure className="m-0 min-w-0">
      <div role="img" aria-label={label} style={{ width: "100%", height }}>
        {children}
      </div>
      {legend && <figcaption className="mt-2 flex flex-wrap gap-2">{legend}</figcaption>}
    </figure>
  );
}

export function LegendSwatch({ color, label, dashed }: { color: string; label: string; dashed?: boolean }) {
  return (
    <span className="neo-mono inline-flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-[0.1em]">
      <svg width="18" height="8" aria-hidden="true">
        <line x1="0" y1="4" x2="18" y2="4" stroke={color} strokeWidth="3" strokeDasharray={dashed ? "4 3" : undefined} />
      </svg>
      {label}
    </span>
  );
}
