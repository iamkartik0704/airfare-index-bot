import type { ReactNode } from "react";
import { cn } from "@/lib/format";

export interface Column {
  key: string;
  label: ReactNode;
  align?: "left" | "right" | "center";
  /** When set, the header is a sort button. */
  sortable?: boolean;
  className?: string;
}

export interface SortState {
  key: string;
  dir: "asc" | "desc";
}

/** Data table with ink rules and mono figures. Scrolls horizontally on phones. */
export function Table({
  columns,
  caption,
  children,
  className,
  sort,
  onSort,
  minWidth,
}: {
  columns: Array<Column | string>;
  caption: string;
  children: ReactNode;
  className?: string;
  sort?: SortState;
  onSort?: (key: string) => void;
  minWidth?: number;
}) {
  const cols: Column[] = columns.map((c) => (typeof c === "string" ? { key: c, label: c } : c));
  return (
    <div className={cn("neo-scroll -mx-1 overflow-x-auto px-1", className)} tabIndex={0} role="region" aria-label={caption}>
      <table className="w-full border-collapse text-left" style={minWidth ? { minWidth } : undefined}>
        <caption className="sr-only">{caption}</caption>
        <thead>
          <tr className="border-b-[3px] border-ink">
            {cols.map((c) => {
              const active = sort?.key === c.key;
              const ariaSort = active ? (sort.dir === "asc" ? "ascending" : "descending") : undefined;
              const align = c.align === "right" ? "text-right" : c.align === "center" ? "text-center" : "text-left";
              return (
                <th
                  key={c.key}
                  scope="col"
                  aria-sort={c.sortable ? (ariaSort ?? "none") : undefined}
                  className={cn(
                    "neo-mono px-2 py-2 text-[10px] font-bold uppercase tracking-[0.12em] whitespace-nowrap text-muted-foreground",
                    align,
                    c.className,
                  )}
                >
                  {c.sortable && onSort ? (
                    <button
                      type="button"
                      onClick={() => onSort(c.key)}
                      className={cn("inline-flex items-center gap-1 uppercase", active && "text-ink")}
                    >
                      {c.label}
                      <span aria-hidden="true">{active ? (sort.dir === "asc" ? "▲" : "▼") : "↕"}</span>
                    </button>
                  ) : (
                    c.label
                  )}
                </th>
              );
            })}
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
  onClick,
  label,
}: {
  children: ReactNode;
  className?: string;
  onClick?: () => void;
  label?: string;
}) {
  const interactive = Boolean(onClick);
  return (
    <tr
      className={cn(
        "border-b-2 border-ink/10 hover:bg-yellow/30",
        interactive && "cursor-pointer focus-visible:bg-yellow/40",
        className,
      )}
      onClick={onClick}
      tabIndex={interactive ? 0 : undefined}
      aria-label={label}
      onKeyDown={
        interactive
          ? (e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onClick?.();
              }
            }
          : undefined
      }
    >
      {children}
    </tr>
  );
}

export function TD({
  children,
  className,
  mono = true,
  align,
}: {
  children: ReactNode;
  className?: string;
  mono?: boolean;
  align?: "left" | "right" | "center";
}) {
  return (
    <td
      className={cn(
        mono && "neo-mono",
        "px-2 py-1.5 text-xs whitespace-nowrap",
        align === "right" && "text-right",
        align === "center" && "text-center",
        className,
      )}
    >
      {children}
    </td>
  );
}
