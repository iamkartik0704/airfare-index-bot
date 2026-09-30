import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

/** Panel — the single container primitive. Square, ink-bordered, hard shadow. */
export function Panel({
  title,
  kicker,
  right,
  children,
  className,
  tone = "paper",
  shadow = true,
}: {
  title?: ReactNode;
  kicker?: ReactNode;
  right?: ReactNode;
  children: ReactNode;
  className?: string;
  tone?: "paper" | "blue" | "yellow" | "red" | "green" | "violet" | "ink";
  shadow?: boolean;
}) {
  const tones: Record<string, string> = {
    paper: "bg-card",
    blue: "bg-[#2b4cff] text-white",
    yellow: "bg-[#ffd400] text-[#0b0b0b]",
    red: "bg-[#ff4a1c] text-white",
    green: "bg-[#00a878] text-white",
    violet: "bg-[#b14eff] text-white",
    ink: "bg-[#0b0b0b] text-[#f2efe6]",
  };
  return (
    <section
      className={cn(
        "neo neo-press relative flex flex-col",
        shadow && "neo-shadow",
        tones[tone],
        className,
      )}
    >
      {(title || right || kicker) && (
        <header className="flex flex-wrap items-center justify-between gap-3 border-b-[3px] border-current/20 px-4 py-3">
          <div className="min-w-0">
            {kicker && (
              <p className="neo-mono text-[10px] font-bold uppercase tracking-[0.18em] opacity-70">
                {kicker}
              </p>
            )}
            {title && <h2 className="neo-display text-lg md:text-xl">{title}</h2>}
          </div>
          {right && <div className="shrink-0">{right}</div>}
        </header>
      )}
      <div className="flex-1 p-4">{children}</div>
    </section>
  );
}

/** Stat — the big-number block. */
export function Stat({
  label,
  value,
  unit,
  delta,
  hint,
  tone = "ink",
}: {
  label: string;
  value: ReactNode;
  unit?: string;
  delta?: number;
  hint?: ReactNode;
  tone?: "ink" | "blue" | "yellow" | "green" | "red";
}) {
  const tones: Record<string, string> = {
    ink: "bg-white",
    blue: "bg-[#2b4cff] text-white",
    yellow: "bg-[#ffd400] text-[#0b0b0b]",
    green: "bg-[#00a878] text-white",
    red: "bg-[#ff4a1c] text-white",
  };
  const dir = delta === undefined ? null : delta > 0 ? "▲" : delta < 0 ? "▼" : "■";
  const dirColor =
    delta === undefined || delta === 0
      ? "bg-[#e6e1d4] text-[#0b0b0b]"
      : delta > 0
        ? "bg-[#ff4a1c] text-white"
        : "bg-[#00a878] text-white";
  return (
    <div className={cn("neo-2 neo-shadow-sm flex flex-col gap-2 p-3", tones[tone])}>
      <p className="neo-mono text-[10px] font-bold uppercase tracking-[0.16em] opacity-70">{label}</p>
      <div className="flex items-end gap-2">
        <span className="neo-display text-3xl leading-none md:text-4xl">{value}</span>
        {unit && <span className="neo-mono pb-1 text-xs font-bold opacity-70">{unit}</span>}
        {delta !== undefined && (
          <span
            className={cn(
              "neo-mono neo-2 mb-0.5 ml-auto px-1.5 py-0.5 text-[11px] font-bold",
              dirColor,
            )}
          >
            {dir} {Math.abs(delta).toFixed(2)}%
          </span>
        )}
      </div>
      {hint && <p className="neo-mono text-[10px] leading-4 opacity-70">{hint}</p>}
    </div>
  );
}

export function Tag({
  children,
  tone = "paper",
  className,
}: {
  children: ReactNode;
  tone?: "paper" | "blue" | "yellow" | "red" | "green" | "violet" | "ink" | "white";
  className?: string;
}) {
  const tones: Record<string, string> = {
    paper: "bg-[#e6e1d4] text-[#0b0b0b]",
    white: "bg-white text-[#0b0b0b]",
    blue: "bg-[#2b4cff] text-white",
    yellow: "bg-[#ffd400] text-[#0b0b0b]",
    red: "bg-[#ff4a1c] text-white",
    green: "bg-[#00a878] text-white",
    violet: "bg-[#b14eff] text-white",
    ink: "bg-[#0b0b0b] text-[#f2efe6]",
  };
  return (
    <span
      className={cn(
        "neo-2 inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-[0.12em]",
        tones[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}

const BTN_BASE =
  "neo-2 neo-shadow-xs neo-press inline-flex items-center justify-center gap-2 px-3 py-1.5 text-xs font-bold uppercase tracking-[0.1em] disabled:opacity-50";

export function Btn({
  children,
  tone = "yellow",
  className,
  ...rest
}: {
  children: ReactNode;
  tone?: "yellow" | "blue" | "white" | "ink" | "red" | "green";
} & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  const tones: Record<string, string> = {
    yellow: "bg-[#ffd400] text-[#0b0b0b]",
    blue: "bg-[#2b4cff] text-white",
    white: "bg-white text-[#0b0b0b]",
    ink: "bg-[#0b0b0b] text-[#f2efe6]",
    red: "bg-[#ff4a1c] text-white",
    green: "bg-[#00a878] text-white",
  };
  return (
    <button className={cn(BTN_BASE, tones[tone], className)} {...rest}>
      {children}
    </button>
  );
}

export function BtnLink({
  children,
  to,
  tone = "ink",
  className,
}: {
  children: ReactNode;
  to: string;
  tone?: "yellow" | "blue" | "white" | "ink" | "red" | "green";
  className?: string;
}) {
  const tones: Record<string, string> = {
    yellow: "bg-[#ffd400] text-[#0b0b0b]",
    blue: "bg-[#2b4cff] text-white",
    white: "bg-white text-[#0b0b0b]",
    ink: "bg-[#0b0b0b] text-[#f2efe6]",
    red: "bg-[#ff4a1c] text-white",
    green: "bg-[#00a878] text-white",
  };
  return (
    <a href={to} className={cn(BTN_BASE, tones[tone], className)}>
      {children}
    </a>
  );
}

/** Data table with ink rules and mono figures. */
export function Table({ head, children, className }: { head: string[]; children: ReactNode; className?: string }) {
  return (
    <div className={cn("neo-scroll overflow-x-auto", className)}>
      <table className="w-full border-collapse text-left">
        <thead>
          <tr className="border-b-[3px] border-[#0b0b0b]">
            {head.map((h) => (
              <th
                key={h}
                className="neo-mono whitespace-nowrap px-3 py-2 text-[10px] font-bold uppercase tracking-[0.14em] text-muted-foreground"
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}

export function TR({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return <tr className={cn("border-b-2 border-[#0b0b0b]/15 hover:bg-[#ffd400]/30", className)}>{children}</tr>;
}

export function TD({
  children,
  className,
  mono = true,
}: {
  children: ReactNode;
  className?: string;
  mono?: boolean;
}) {
  return (
    <td className={cn(mono && "neo-mono", "px-3 py-1.5 text-xs", className)}>{children}</td>
  );
}

/** Signed change, coloured by direction (red = up in India, green = down). */
export function Delta({ value, suffix = "%" }: { value: number; suffix?: string }) {
  const up = value > 0;
  const flat = Math.abs(value) < 0.005;
  return (
    <span
      className={cn(
        "neo-mono neo-2 px-1 py-0.5 text-[10px] font-bold",
        flat ? "bg-[#e6e1d4]" : up ? "bg-[#ff4a1c] text-white" : "bg-[#00a878] text-white",
      )}
    >
      {flat ? "0.00" : `${up ? "+" : ""}${value.toFixed(2)}`}
      {suffix}
    </span>
  );
}

/** Divider label used inside panels. */
export function Label({ children, right }: { children: ReactNode; right?: ReactNode }) {
  return (
    <div className="mb-3 flex items-center justify-between gap-3">
      <p className="neo-mono text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground">
        {children}
      </p>
      {right}
    </div>
  );
}

/** Horizontal magnitude bar with an ink border — used for weights, funnels. */
export function Bar({
  value,
  max,
  tone = "blue",
  height = 14,
}: {
  value: number;
  max: number;
  tone?: "blue" | "red" | "green" | "yellow" | "violet" | "ink";
  height?: number;
}) {
  const tones: Record<string, string> = {
    blue: "bg-[#2b4cff]",
    red: "bg-[#ff4a1c]",
    green: "bg-[#00a878]",
    yellow: "bg-[#ffd400]",
    violet: "bg-[#b14eff]",
    ink: "bg-[#0b0b0b]",
  };
  const pct = max === 0 ? 0 : Math.min(100, Math.abs(value / max) * 100);
  return (
    <div className="neo-2 w-full bg-white" style={{ height }}>
      <div className={cn("h-full", tones[tone])} style={{ width: `${pct}%` }} />
    </div>
  );
}

/** Pipeline flow node — used by the architecture diagram and the pipeline page. */
export function FlowNode({
  title,
  sub,
  tone = "white",
  className,
}: {
  title: ReactNode;
  sub?: ReactNode;
  tone?: "white" | "blue" | "yellow" | "red" | "green" | "ink" | "violet";
  className?: string;
}) {
  const tones: Record<string, string> = {
    white: "bg-white text-[#0b0b0b]",
    blue: "bg-[#2b4cff] text-white",
    yellow: "bg-[#ffd400] text-[#0b0b0b]",
    red: "bg-[#ff4a1c] text-white",
    green: "bg-[#00a878] text-white",
    ink: "bg-[#0b0b0b] text-[#f2efe6]",
    violet: "bg-[#b14eff] text-white",
  };
  return (
    <div className={cn("neo-2 neo-shadow-xs flex flex-col gap-1 p-2.5", tones[tone], className)}>
      <p className="text-[11px] font-extrabold uppercase leading-tight tracking-tight">{title}</p>
      {sub && <p className="neo-mono text-[9.5px] leading-[1.35] opacity-80">{sub}</p>}
    </div>
  );
}

export function Arrow({ label, vertical = false }: { label?: string; vertical?: boolean }) {
  return (
    <div
      className={cn(
        "flex items-center justify-center",
        vertical ? "flex-col" : "flex-row",
      )}
    >
      {vertical ? (
        <span className="neo-mono text-lg font-black leading-none">↓</span>
      ) : (
        <span className="neo-mono text-lg font-black leading-none">→</span>
      )}
      {label && (
        <span className="neo-mono px-1 text-[9px] font-bold uppercase tracking-widest text-muted-foreground">
          {label}
        </span>
      )}
    </div>
  );
}

export function KeyVal({ k, v }: { k: ReactNode; v: ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-3 border-b-2 border-[#0b0b0b]/12 py-1.5 last:border-0">
      <span className="neo-mono text-[10px] font-bold uppercase tracking-[0.12em] text-muted-foreground">
        {k}
      </span>
      <span className="neo-mono text-xs font-bold">{v}</span>
    </div>
  );
}

export function Loading({ label = "Computing index" }: { label?: string }) {
  return (
    <div className="flex min-h-[75vh] w-full items-center justify-center p-4">
      <div className="neo neo-shadow inline-flex items-center gap-3 bg-white px-6 py-4">
        <span className="neo-live text-xl">■</span>
        <span className="neo-mono text-xs font-bold uppercase tracking-[0.2em]">{label}…</span>
      </div>
    </div>
  );
}

export function Empty({ label }: { label: string }) {
  return (
    <div className="neo-dotted flex items-center justify-center border-[3px] border-dashed border-[#0b0b0b]/40 p-6">
      <span className="neo-mono text-[11px] font-bold uppercase tracking-[0.16em] text-muted-foreground">
        {label}
      </span>
    </div>
  );
}
