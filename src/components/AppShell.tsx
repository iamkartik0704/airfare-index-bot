import { useMutation, useQuery } from "convex/react";
import { api } from "@/convex/_generated/api";
import { NavLink, Outlet, useNavigate } from "react-router";
import {
  Activity,
  BarChart3,
  Boxes,
  Flame,
  FlaskConical,
  Grid3x3,
  Layers,
  LogOut,
  Plane,
  Play,
  Presentation,
  Route as RouteIcon,
  ScrollText,
  ShieldCheck,
  TrendingUp,
} from "lucide-react";
import { useState } from "react";
import { useAuth } from "@/hooks/use-auth";
import { cn } from "@/lib/utils";
import { Btn, Tag } from "@/components/neo";

const NAV = [
  { to: "/dashboard", label: "Index", icon: TrendingUp, end: true, note: "Daily APIx" },
  { to: "/dashboard/sectors", label: "Sectors", icon: Grid3x3, note: "Route heat-map" },
  { to: "/dashboard/leadtime", label: "Lead time", icon: BarChart3, note: "Booking curve" },
  { to: "/dashboard/drivers", label: "Drivers", icon: Flame, note: "What moved it" },
  { to: "/dashboard/pipeline", label: "Collector", icon: Boxes, note: "Scraping engine" },
  { to: "/dashboard/explorer", label: "Explorer", icon: Layers, note: "Raw → cleaned" },
  { to: "/dashboard/validation", label: "Validation", icon: FlaskConical, note: "DGCA back-test" },
  { to: "/dashboard/methodology", label: "Methodology", icon: ScrollText, note: "PSI + weights" },
  { to: "/dashboard/api", label: "API", icon: RouteIcon, note: "NSO / RBI" },
  { to: "/dashboard/deck", label: "Deck", icon: Presentation, note: "PPT mode" },
];

export default function AppShell() {
  const { signOut } = useAuth();
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const headline = useQuery(api.apix.headline);
  const runSweep = useMutation(api.pipeline.runSweep);
  const [open, setOpen] = useState(false);

  const run = async () => {
    setBusy(true);
    try {
      await runSweep({});
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col bg-background">
      {/* top strip */}
      <header className="neo sticky top-0 z-30 flex flex-wrap items-stretch gap-0 border-x-0 border-t-0 bg-white">
        <div className="flex items-center gap-2 border-r-[3px] border-[#0b0b0b] bg-[#0b0b0b] px-4 py-2.5 text-[#f2efe6]">
          <span className="flex h-7 w-7 items-center justify-center bg-[#ffd400] text-[#0b0b0b]">
            <Plane className="h-4 w-4" />
          </span>
          <div className="leading-none">
            <p className="neo-display text-base">SAFAR</p>
            <p className="neo-mono text-[9px] uppercase tracking-[0.18em] opacity-70">
              PS 26056 · MoSPI
            </p>
          </div>
        </div>

        <div className="flex flex-1 flex-wrap items-center gap-x-5 gap-y-1 px-4 py-2">
          <div className="flex items-baseline gap-2">
            <span className="neo-mono text-[10px] font-bold uppercase tracking-[0.16em] text-muted-foreground">
              APIx
            </span>
            <span className="neo-display text-2xl">
              {headline ? headline.index.toFixed(2) : "—"}
            </span>
            <span className="neo-mono text-[10px] text-muted-foreground">
              {headline?.date ?? ""}
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <Tag tone="paper">MoM {headline ? `${headline.momPct >= 0 ? "+" : ""}${headline.momPct.toFixed(2)}%` : "—"}</Tag>
            <Tag tone="red">YoY {headline ? `${headline.yoy >= 0 ? "+" : ""}${headline.yoy.toFixed(2)}%` : "—"}</Tag>
            <Tag tone="green">Basket ₹{headline?.avgFare.toLocaleString("en-IN") ?? "—"}</Tag>
          </div>
        </div>

        <div className="flex items-center gap-2 border-l-[3px] border-[#0b0b0b] px-3 py-2">
          <Btn tone="yellow" onClick={run} disabled={busy}>
            <Play className="h-3.5 w-3.5" />
            {busy ? "Collecting…" : "Run pipeline"}
          </Btn>
          <button
            className="neo-2 neo-shadow-xs neo-press flex h-8 w-8 items-center justify-center bg-white lg:hidden"
            onClick={() => setOpen((v) => !v)}
            aria-label="Toggle navigation"
          >
            <Activity className="h-4 w-4" />
          </button>
        </div>
      </header>

      <div className="flex flex-1 flex-col lg:flex-row">
        {/* sidebar */}
        <nav
          className={cn(
            "neo shrink-0 border-x-0 border-b-0 bg-white lg:block lg:w-[248px] lg:border-r-[3px] lg:border-[#0b0b0b]",
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
                      "flex items-center gap-3 border-b-2 border-[#0b0b0b]/15 px-4 py-2.5 transition-none",
                      isActive
                        ? "bg-[#ffd400] text-[#0b0b0b]"
                        : "bg-white hover:bg-[#e6e1d4]",
                    )
                  }
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  <span className="flex-1">
                    <span className="block text-[13px] font-extrabold uppercase leading-tight tracking-tight">
                      {label}
                    </span>
                    <span className="neo-mono block text-[9.5px] uppercase tracking-[0.14em] text-muted-foreground">
                      {note}
                    </span>
                  </span>
                </NavLink>
              </li>
            ))}
          </ul>

          <div className="neo-mono space-y-2 p-4 text-[9.5px] uppercase tracking-[0.14em] text-muted-foreground">
            <p className="flex items-center gap-1.5">
              <ShieldCheck className="h-3.5 w-3.5" /> robots.txt enforced
            </p>
            <p className="flex items-center gap-1.5">
              <Boxes className="h-3.5 w-3.5" /> epoch {headline?.epoch ?? 1} ·{" "}
              {headline?.runs ?? 0} runs
            </p>
            <button
              className="neo-2 neo-shadow-xs neo-press flex w-full items-center justify-center gap-2 bg-white px-2 py-1.5 text-[10px] font-bold uppercase tracking-[0.12em] text-[#0b0b0b]"
              onClick={async () => {
                await signOut();
                navigate("/");
              }}
            >
              <LogOut className="h-3.5 w-3.5" /> Sign out
            </button>
          </div>
        </nav>

        <main className="neo-grid flex-1 p-4 md:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
