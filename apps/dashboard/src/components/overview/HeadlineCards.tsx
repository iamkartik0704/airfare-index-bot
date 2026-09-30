import type { Headline } from "@/api/types";
import { MethodologyStatusBadges } from "@/components/honesty";
import { Delta, KeyVal, Panel, Stat } from "@/components/neo";
import { date, dateTime, fixed, inr, int, pct, ratioPct } from "@/lib/format";

export function HeadlineCards({ h }: { h: Headline }) {
  const base = h.base_period ? `${date(h.base_period[0])} – ${date(h.base_period[1])}` : "not set";
  return (
    <div className="grid gap-3 lg:grid-cols-[1.4fr_1fr]">
      <div className="grid gap-3 sm:grid-cols-2">
        <Stat
          tone="blue"
          label={`APIx · ${date(h.date)}`}
          value={fixed(h.value, 2)}
          delta={h.change_dod_pct}
          deltaLabel="DoD"
          hint={`Quality-adjusted, base period = 100 · nominal ${fixed(h.nominal_value, 2)}`}
        />
        <Stat label="7-day rolling APIx" value={fixed(h.rolling_value, 2)} hint="Trailing mean published by the index engine" />
        <Stat
          tone="yellow"
          label="Avg basket fare"
          value={inr(h.avg_fare)}
          hint="Weighted basket, economy, all-in (taxes + fees)"
        />
        <Stat
          label="Coverage"
          value={pct(h.coverage_pct, 1)}
          hint={`Imputed share ${ratioPct(h.imputed_share, 1)} · ${int(h.observation_count)} quotes`}
        />
      </div>
      <Panel kicker="Release" title="Changes & provenance">
        <div className="mb-3 flex flex-wrap gap-2">
          <Delta value={h.change_dod_pct} label="DoD" />
          <Delta value={h.change_wow_pct} label="WoW" />
          <Delta value={h.change_mom_pct} label="MoM" />
        </div>
        <KeyVal k="Index date" v={date(h.date)} />
        <KeyVal k="Base period (= 100)" v={base} />
        <KeyVal k="Computed at" v={dateTime(h.computed_at)} />
        <KeyVal k="Observations" v={int(h.observation_count)} />
        <KeyVal k="Data origin" v={h.data_origin.toUpperCase()} />
        <div className="mt-3">
          <p className="neo-mono mb-1.5 text-[10px] font-bold tracking-[0.14em] text-muted-foreground uppercase">
            Methodology status
          </p>
          <MethodologyStatusBadges status={h.methodology_status} />
        </div>
      </Panel>
    </div>
  );
}
