import {
  Activity,
  BarChart3,
  Boxes,
  FlaskConical,
  Grid3x3,
  Layers,
  Menu,
  Plane,
  Route as RouteIcon,
  ScrollText,
  ShieldCheck,
  TrendingUp,
  X,
} from "lucide-react";
import { useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router";
import { ApiError } from "@/api/client";
import { useHeadline, useSystemHealth } from "@/api/queries";
import { cn, duration, fixed } from "@/lib/format";
import { DataOriginBanner } from "./honesty";
import { Delta, Tag } from "./neo";

const NAV = [
  { to: "/", label: "Index", icon: TrendingUp, end: true, note: "Daily APIx" },
  { to: "/sectors", label: "Sectors", icon: Grid3x3, note: "Route heat-map" },
  { to: "/lead-time", label: "Lead time", icon: BarChart3, note: "Booking curve" },
  { to: "/explorer", label: "Explorer", icon: Layers, note: "Raw → cleaned" },
  { to: "/pipeline", label: "Pipeline", icon: Boxes, note: "System console" },
  { to: "/validation", label: "Validation", icon: FlaskConical, note: "Back-test" },
  { to: "/methodology", label: "Methodology", icon: ScrollText, note: "Basket + rules" },
  { to: "/api", label: "API", icon: RouteIcon, note: "Endpoints" },
];

function HealthTag() {
  const health = useSystemHealth();
  if (health.isPending) return <Tag tone="paper">API …</Tag>;
  if (health.isError) {
    const code = health.error instanceof ApiError ? health.error.status : 0;
    return <Tag tone="red">API unreachable{code ? ` · ${code}` : ""}</Tag>;
  }
  const h = health.data;
  const tone = h.status === "ok" ? "green" : h.status === "degraded" ? "yellow" : "red";
  return (
    <>
      <Tag tone={tone}>
        <Activity className="h-3 w-3" aria-hidden="true" /> System {h.status}
      </Tag>
      {h.freshness.stale && <Tag tone="red">Stale · {duration(h.freshness.age_seconds)}</Tag>}
    </>
  );
}

function HeadlineStrip() {
  const headline = useHeadline();
  const h = headline.data;
  return (
    <div className="flex min-w-0 flex-1 flex-wrap items-center gap-x-4 gap-y-1 px-3 py-2 sm:px-4">
      <div className="flex items-baseline gap-2">
        <span className="neo-mono text-[10px] font-bold uppercase tracking-[0.16em] text-muted-foreground">APIx</span>
        <span className="neo-display text-2xl">{h ? fixed(h.value, 2) : "—"}</span>
        <span className="neo-mono text-[10px] text-muted-foreground">{h?.date ?? (headline.isError ? "no index yet" : "")}</span>
      </div>
      {h && (
        <div className="hidden flex-wrap items-center gap-1.5 sm:flex">
          <Delta value={h.change_dod_pct} label="DoD" />
          <Delta value={h.change_mom_pct} label="MoM" />
        </div>
      )}
      <div className="flex flex-wrap items-center gap-1.5">
        <HealthTag />
      </div>
    </div>
  );
}

export default function AppShell() {
  const [open, setOpen] = useState(false);
  const headline = useHeadline();
  const location = useLocation();

  return (
    <div className="flex min-h-screen flex-col bg-paper">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:bg-yellow focus:p-2 focus:font-bold"
      >
        Skip to content
      </a>
      <header className="sticky top-0 z-30 flex items-stretch border-b-[3px] border-ink bg-white">
        <div className="flex items-center gap-2 border-r-[3px] border-ink bg-ink px-3 py-2.5 text-paper sm:px-4">
          <span className="flex h-7 w-7 items-center justify-center bg-yellow text-ink">
            <Plane className="h-4 w-4" aria-hidden="true" />
          </span>
          <div className="leading-none">
            <p className="neo-display text-base">SAFAR</p>
            <p className="neo-mono text-[9px] uppercase tracking-[0.18em] opacity-70">SIH 26056 · MoSPI</p>
          </div>
        </div>
        <HeadlineStrip />
        <div className="flex items-center border-l-[3px] border-ink px-2 lg:hidden">
          <button
            type="button"
            className="neo-2 neo-shadow-xs neo-press flex h-9 w-9 items-center justify-center bg-white"
            onClick={() => setOpen((v) => !v)}
            aria-label={open ? "Close navigation" : "Open navigation"}
            aria-expanded={open}
            aria-controls="primary-nav"
          >
            {open ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
          </button>
        </div>
      </header>

      <div className="flex flex-1 flex-col lg:flex-row">
        <nav
          id="primary-nav"
          aria-label="Primary"
          className={cn(
            "shrink-0 border-b-[3px] border-ink bg-white lg:block lg:w-[232px] lg:border-r-[3px] lg:border-b-0",
            open ? "block" : "hidden",
          )}
        >
          <ul>
            {NAV.map(({ to, label, icon: Icon, note, end }) => (
              <li key={to}>
                <NavLink
                  to={to}
                  end={end}
                  onClick={() => setOpen(false)}
                  className={({ isActive }) =>
                    cn(
                      "flex items-center gap-3 border-b-2 border-ink/10 px-4 py-2.5",
                      isActive || (to === "/sectors" && location.pathname.startsWith("/routes/"))
                        ? "bg-yellow text-ink"
                        : "bg-white hover:bg-muted",
                    )
                  }
                >
                  <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
                  <span className="flex-1">
                    <span className="block text-[13px] leading-tight font-extrabold tracking-tight uppercase">{label}</span>
                    <span className="neo-mono block text-[9.5px] tracking-[0.14em] text-muted-foreground uppercase">{note}</span>
                  </span>
                </NavLink>
              </li>
            ))}
          </ul>
          <div className="neo-mono space-y-2 p-4 text-[9.5px] tracking-[0.14em] text-muted-foreground uppercase">
            <p className="flex items-center gap-1.5">
              <ShieldCheck className="h-3.5 w-3.5" aria-hidden="true" /> Read-only dashboard
            </p>
            <p className="normal-case tracking-normal">
              All figures come from the SAFAR API (/api/v1). Nothing is computed in the browser.
            </p>
          </div>
        </nav>

        <main id="main" className="neo-grid min-w-0 flex-1 p-3 sm:p-4 md:p-6">
          {/* Persistent, app-wide honesty banner driven by the headline's data_origin. */}
          <DataOriginBanner origin={headline.data?.data_origin} className="mb-4" />
          <Outlet />
        </main>
      </div>
    </div>
  );
}
