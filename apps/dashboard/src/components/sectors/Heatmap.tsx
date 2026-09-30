import { Link } from "react-router";
import type { HeatmapOut } from "@/api/types";
import { fixed, monthLabel, num, shortDate } from "@/lib/format";

/** Diverging scale: red = fares rising, blue = falling; saturation by magnitude (display only). */
function tone(change: number | null): { bg: string; fg: string } {
  if (change === null) return { bg: "#e6e1d4", fg: "#5c5747" };
  const a = Math.min(Math.abs(change) / 8, 1);
  const alpha = 0.12 + a * 0.88;
  const bg = change >= 0 ? `rgba(255,74,28,${alpha})` : `rgba(43,76,255,${alpha})`;
  return { bg, fg: alpha > 0.5 ? "#ffffff" : "#0b0b0b" };
}

/** Route × period grid, rows in the order given (basket weight order from /routes). */
export function Heatmap({ data, routeOrder }: { data: HeatmapOut; routeOrder: string[] }) {
  const byKey = new Map(data.cells.map((c) => [`${c.route}|${c.period}`, c]));
  const cellRoutes = new Set(data.cells.map((c) => c.route));
  const routes = [...routeOrder.filter((r) => cellRoutes.has(r)), ...[...cellRoutes].filter((r) => !routeOrder.includes(r))];
  const fmt = data.frequency.toUpperCase() === "MONTHLY" ? monthLabel : shortDate;
  const regionOf = new Map(data.cells.map((c) => [c.route, c.region]));

  return (
    <div className="neo-scroll overflow-x-auto pb-1" tabIndex={0} role="region" aria-label="Sector heat-map, scrollable">
      <table className="border-separate border-spacing-[2px]" style={{ minWidth: 120 + data.periods.length * 64 }}>
        <caption className="sr-only">
          Change in route index by {data.frequency.toLowerCase()} period, percent. Red means fares rose, blue means fares fell.
        </caption>
        <thead>
          <tr>
            <th scope="col" className="neo-mono sticky left-0 z-10 bg-white px-1 text-left text-[10px] uppercase">
              Route
            </th>
            {data.periods.map((p) => (
              <th key={p} scope="col" className="neo-mono px-1 py-1 text-center text-[10px] font-bold tracking-wider whitespace-nowrap uppercase">
                {fmt(p)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {routes.map((route) => (
            <tr key={route}>
              <th scope="row" className="sticky left-0 z-10 bg-white p-0 text-left">
                <Link to={`/routes/${route}`} className="neo-2 flex flex-col justify-center bg-white px-2 py-1 hover:bg-yellow">
                  <span className="neo-mono text-[11px] leading-none font-bold">{route}</span>
                  <span className="neo-mono text-[9px] text-muted-foreground">{regionOf.get(route)}</span>
                </Link>
              </th>
              {data.periods.map((p) => {
                const cell = byKey.get(`${route}|${p}`);
                const change = num(cell?.change_pct);
                const { bg, fg } = tone(change);
                const text = !cell ? "·" : change === null ? "—" : `${change > 0 ? "+" : ""}${fixed(change, 1)}`;
                return (
                  <td
                    key={p}
                    title={cell ? `${route} · ${fmt(p)} · index ${fixed(cell.value, 2)} · change ${text}%` : `${route} · ${fmt(p)} · no value`}
                    className="neo-2 neo-mono h-10 min-w-[56px] text-center text-[11px] font-bold"
                    style={{ background: bg, color: fg }}
                  >
                    {text}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
