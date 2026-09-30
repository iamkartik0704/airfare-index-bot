import { FlaskConical, Scale, ShieldAlert } from "lucide-react";
import type { DataOrigin } from "@/api/types";
import { cn, humanize } from "@/lib/format";
import { Tag } from "./neo";

/*
 * Honesty about synthetic data is a hard requirement: anything that is not
 * observed live data is labelled persistently and in plain language.
 */

export const ORIGIN_COPY: Record<Exclude<DataOrigin, "live">, { title: string; body: string }> = {
  simulated: {
    title: "SIMULATED DATA",
    body: "Synthetic demonstration source — these are not observed fares.",
  },
  mixed: {
    title: "MIXED DATA",
    body: "Contains synthetic demonstration quotes alongside observed fares — do not treat as an official statistic.",
  },
  none: {
    title: "NO DATA",
    body: "No observations contribute to this view yet.",
  },
};

/** Full-width persistent banner for a view whose `data_origin` is not "live". */
export function DataOriginBanner({ origin, className }: { origin: DataOrigin | undefined; className?: string }) {
  if (!origin || origin === "live") return null;
  const copy = ORIGIN_COPY[origin];
  return (
    <div
      role="note"
      aria-label={`${copy.title}: ${copy.body}`}
      className={cn(
        "neo-2 flex flex-wrap items-center gap-x-3 gap-y-1 px-3 py-2",
        origin === "none" ? "bg-muted" : "bg-yellow",
        className,
      )}
    >
      <span className="flex items-center gap-2">
        <FlaskConical className="h-4 w-4 shrink-0" aria-hidden="true" />
        <span className="text-xs font-black tracking-[0.08em] uppercase">{copy.title}</span>
      </span>
      <span className="neo-mono text-[11px] leading-4">{copy.body}</span>
    </div>
  );
}

/** Compact badge for panels/charts carrying their own `data_origin`. */
export function OriginBadge({ origin }: { origin: DataOrigin | undefined }) {
  if (!origin) return null;
  if (origin === "live") return <Tag tone="green">Live data</Tag>;
  if (origin === "none") return <Tag tone="paper">No data</Tag>;
  return (
    <Tag tone="yellow" title={ORIGIN_COPY[origin].body}>
      <FlaskConical className="h-3 w-3" aria-hidden="true" />
      {origin === "simulated" ? "Simulated" : "Mixed · incl. simulated"}
    </Tag>
  );
}

export function SyntheticBenchmarkBanner({ label }: { label?: string }) {
  return (
    <div role="note" className="neo-2 flex flex-wrap items-center gap-x-3 gap-y-1 bg-red px-3 py-2 text-white">
      <span className="flex items-center gap-2">
        <ShieldAlert className="h-4 w-4 shrink-0" aria-hidden="true" />
        <span className="text-xs font-black tracking-[0.08em] uppercase">SYNTHETIC BENCHMARK — not DGCA data</span>
      </span>
      <span className="neo-mono text-[11px] leading-4">
        {label ? `"${label}" is ` : "The benchmark is "}a generated placeholder series. Load the real DGCA series with{" "}
        <code className="bg-white/20 px-1">scripts/db/load_dgca_benchmark.py</code>.
      </span>
    </div>
  );
}

/** Basket weights / hedonic factors are indicative until official values are loaded. */
export function MethodologyStatusBadges({ status }: { status: Record<string, string> | undefined }) {
  if (!status) return null;
  const entries = Object.entries(status);
  if (!entries.length) return null;
  return (
    <div className="flex flex-wrap gap-1.5">
      {entries.map(([k, v]) => (
        <Tag
          key={k}
          tone={v.toUpperCase() === "INDICATIVE" ? "violet" : v.toUpperCase() === "OFFICIAL" ? "green" : "white"}
          title={v.toUpperCase() === "INDICATIVE" ? "Indicative weights, awaiting official PSD/DGCA values" : undefined}
        >
          {humanize(k)}: {v}
        </Tag>
      ))}
    </div>
  );
}

export function IndicativeNote({ status }: { status: Record<string, string> | undefined }) {
  const indicative = Object.entries(status ?? {}).filter(([, v]) => v.toUpperCase() === "INDICATIVE");
  if (!indicative.length) return null;
  return (
    <div role="note" className="neo-2 flex flex-wrap items-center gap-x-3 gap-y-1 bg-violet px-3 py-2 text-white">
      <span className="flex items-center gap-2">
        <Scale className="h-4 w-4 shrink-0" aria-hidden="true" />
        <span className="text-xs font-black tracking-[0.08em] uppercase">INDICATIVE METHODOLOGY</span>
      </span>
      <span className="neo-mono text-[11px] leading-4">
        {indicative.map(([k]) => humanize(k)).join(", ")}: indicative weights, awaiting official PSD/DGCA values.
      </span>
    </div>
  );
}
