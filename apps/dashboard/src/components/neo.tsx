import type { ButtonHTMLAttributes, ReactNode } from "react";
import { cn, num, type Numeric } from "@/lib/format";

/* Neo-brutalist primitives, ported from the legacy src/components/neo.tsx. */

export type Tone = "paper" | "white" | "blue" | "yellow" | "red" | "green" | "violet" | "ink";

export const TONE_BG: Record<Tone, string> = {
  paper: "bg-muted text-ink",
  white: "bg-white text-ink",
  blue: "bg-blue text-white",
  yellow: "bg-yellow text-ink",
  red: "bg-red text-white",
  green: "bg-green text-white",
  violet: "bg-violet text-white",
  ink: "bg-ink text-paper",
};

/** Panel — the single container primitive. Square, ink-bordered, hard shadow. */
export function Panel({
  title,
  kicker,
  right,
  children,
  className,
  tone = "white",
  id,
}: {
  title?: ReactNode;
  kicker?: ReactNode;
  right?: ReactNode;
  children: ReactNode;
  className?: string;
  tone?: Tone;
  id?: string;
}) {
  const headingId = id ? `${id}-title` : undefined;
  return (
    <section
      id={id}
      aria-labelledby={headingId}
      className={cn("neo neo-shadow relative flex min-w-0 flex-col", TONE_BG[tone], className)}
    >
      {(title || right || kicker) && (
        <header className="flex flex-wrap items-center justify-between gap-3 border-b-[3px] border-current/15 px-4 py-3">
          <div className="min-w-0">
            {kicker && (
              <p className="neo-mono text-[10px] font-bold uppercase tracking-[0.18em] opacity-70">{kicker}</p>
            )}
            {title && (
              <h2 id={headingId} className="neo-display text-lg md:text-xl">
                {title}
              </h2>
            )}
          </div>
          {right && <div className="flex shrink-0 flex-wrap items-center gap-2">{right}</div>}
        </header>
      )}
      <div className="min-w-0 flex-1 p-3 sm:p-4">{children}</div>
    </section>
  );
}

/** Stat — the big-number block. `delta` is a signed % change from the API. */
export function Stat({
  label,
  value,
  unit,
  delta,
  deltaLabel,
  hint,
  tone = "white",
}: {
  label: string;
  value: ReactNode;
  unit?: string;
  delta?: Numeric;
  deltaLabel?: string;
  hint?: ReactNode;
  tone?: Tone;
}) {
  return (
    <div className={cn("neo-2 neo-shadow-sm flex min-w-0 flex-col gap-2 p-3", TONE_BG[tone])}>
      <p className="neo-mono text-[10px] font-bold uppercase tracking-[0.16em] opacity-75">{label}</p>
      <div className="flex flex-wrap items-end gap-2">
        <span className="neo-display text-3xl leading-none break-all md:text-4xl">{value}</span>
        {unit && <span className="neo-mono pb-1 text-xs font-bold opacity-70">{unit}</span>}
        {delta !== undefined && (
          <span className="ml-auto">
            <Delta value={delta} label={deltaLabel} />
          </span>
        )}
      </div>
      {hint && <div className="neo-mono text-[10px] leading-4 opacity-75">{hint}</div>}
    </div>
  );
}

export function Tag({ children, tone = "paper", className, title }: { children: ReactNode; tone?: Tone; className?: string; title?: string }) {
  return (
    <span
      title={title}
      className={cn(
        "neo-2 inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-[0.12em] whitespace-nowrap",
        TONE_BG[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}

const BTN_BASE =
  "neo-2 neo-shadow-xs neo-press inline-flex items-center justify-center gap-2 px-3 py-1.5 text-xs font-bold uppercase tracking-[0.1em] disabled:opacity-40 disabled:pointer-events-none";

export function Btn({
  children,
  tone = "white",
  active,
  className,
  ...rest
}: { children: ReactNode; tone?: Tone; active?: boolean } & ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type="button"
      aria-pressed={active}
      className={cn(BTN_BASE, TONE_BG[active ? "yellow" : tone], className)}
      {...rest}
    >
      {children}
    </button>
  );
}

/** Segmented toggle (e.g. WEEKLY / MONTHLY). */
export function Segmented<T extends string>({
  options,
  value,
  onChange,
  label,
}: {
  options: { value: T; label: string }[];
  value: T;
  onChange: (v: T) => void;
  label: string;
}) {
  return (
    <div role="group" aria-label={label} className="flex flex-wrap gap-1.5">
      {options.map((o) => (
        <Btn key={o.value} active={o.value === value} onClick={() => onChange(o.value)} className="px-2 py-1 text-[10px]">
          {o.label}
        </Btn>
      ))}
    </div>
  );
}

/** Signed change, coloured by direction (red = fares up, green = fares down). */
export function Delta({ value, label, digits = 2 }: { value: Numeric; label?: string; digits?: number }) {
  const n = num(value);
  if (n === null) {
    return <span className="neo-mono neo-2 bg-muted px-1 py-0.5 text-[10px] font-bold">{label ? `${label} ` : ""}—</span>;
  }
  const flat = Math.abs(n) < 0.005;
  const up = n > 0;
  return (
    <span
      className={cn(
        "neo-mono neo-2 inline-block px-1 py-0.5 text-[10px] font-bold whitespace-nowrap",
        flat ? "bg-muted text-ink" : up ? "bg-red text-white" : "bg-green text-white",
      )}
    >
      {label ? `${label} ` : ""}
      {flat ? "" : up ? "▲ +" : "▼ "}
      {n.toLocaleString("en-IN", { minimumFractionDigits: digits, maximumFractionDigits: digits })}%
    </span>
  );
}

/** Divider label used inside panels. */
export function Label({ children, right }: { children: ReactNode; right?: ReactNode }) {
  return (
    <div className="mt-1 mb-2 flex flex-wrap items-center justify-between gap-2">
      <p className="neo-mono text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground">{children}</p>
      {right}
    </div>
  );
}

/** Horizontal magnitude bar — for weights and funnels. */
export function Bar({ value, max, tone = "blue", height = 14, label }: { value: number; max: number; tone?: Tone; height?: number; label?: string }) {
  const pctWidth = max === 0 ? 0 : Math.min(100, Math.abs(value / max) * 100);
  return (
    <div
      className="neo-2 w-full bg-white"
      style={{ height }}
      role="meter"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={max}
      aria-valuenow={value}
    >
      <div className={cn("h-full", TONE_BG[tone])} style={{ width: `${pctWidth}%` }} />
    </div>
  );
}

export function KeyVal({ k, v }: { k: ReactNode; v: ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-3 border-b-2 border-ink/10 py-1.5 last:border-0">
      <span className="neo-mono text-[10px] font-bold uppercase tracking-[0.12em] text-muted-foreground">{k}</span>
      <span className="neo-mono text-right text-xs font-bold break-all">{v}</span>
    </div>
  );
}

/** Page title block. */
export function PageHeader({ kicker, title, right }: { kicker: string; title: ReactNode; right?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-3">
      <div className="min-w-0">
        <p className="neo-mono text-[10px] font-bold uppercase tracking-[0.24em] text-muted-foreground">{kicker}</p>
        <h1 className="neo-display mt-1 text-3xl sm:text-4xl md:text-5xl">{title}</h1>
      </div>
      {right && <div className="flex flex-wrap items-end gap-2">{right}</div>}
    </div>
  );
}

/** Labelled form control wrapper. */
export function Field({ label, children, htmlFor }: { label: string; children: ReactNode; htmlFor: string }) {
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={htmlFor} className="neo-mono text-[10px] font-bold uppercase tracking-[0.14em]">
        {label}
      </label>
      {children}
    </div>
  );
}

/** Explanatory aside with a dashed border. */
export function Note({ title, children, className }: { title?: string; children: ReactNode; className?: string }) {
  return (
    <div className={cn("border-[3px] border-dashed border-ink/40 bg-white/60 p-3 sm:p-4", className)}>
      {title && (
        <p className="neo-mono text-[10px] font-bold uppercase tracking-[0.18em] text-muted-foreground">{title}</p>
      )}
      <div className="mt-1 text-sm leading-6">{children}</div>
    </div>
  );
}
