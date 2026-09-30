import { useQuery } from "convex/react";
import { api } from "@/convex/_generated/api";
import { Arrow, Bar, FlowNode, KeyVal, Label, Loading, Panel, Stat, Table, TD, TR, Tag } from "@/components/neo";

const STATUS_TONE: Record<string, "green" | "yellow" | "red"> = {
  ok: "green",
  degraded: "yellow",
  blocked: "red",
};

export default function Pipeline() {
  const state = useQuery(api.apix.pipelineState);
  if (!state) return <Loading label="Reading collector registry" />;

  const t = state.totals;
  const runs = state.adapters.map((a) => a.lastRun).filter(Boolean);
  const totalQuotes = t.rawQuotes || 1;

  return (
    <div className="neo-in space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="neo-mono text-[10px] font-bold uppercase tracking-[0.24em] text-muted-foreground">
            Multi-source collection engine
          </p>
          <h1 className="neo-display mt-1 text-4xl md:text-5xl">Collector & compliance</h1>
        </div>
        <div className="flex flex-wrap gap-2">
          <Tag tone="ink">Epoch {state.epoch}</Tag>
          <Tag tone="blue">{t.sources} sources · {t.airlines} airlines · {t.otas} OTAs</Tag>
          <Tag tone="green">robots.txt re-checked every run</Tag>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <Stat label="Requests / sweep" value={t.requests.toLocaleString("en-IN")} hint="24 sectors × 5 windows × 11 sources" tone="blue" />
        <Stat label="Raw quotes" value={t.rawQuotes.toLocaleString("en-IN")} hint="Before cleaning" tone="yellow" />
        <Stat label="Blocked sources" value={t.blocked} hint="Challenge served — recorded, never bypassed" tone={t.blocked > 2 ? "red" : "ink"} />
        <Stat label="HTTP errors" value={t.httpErrors} hint={`${t.retries} retries with exponential backoff`} />
        <Stat label="Jet fuel index" value={state.covariates.atf.toFixed(3)} hint={`USD/INR ${state.covariates.usdInr}`} />
      </div>

      <Panel kicker="End-to-end" title="Pipeline anatomy">
        <div className="flex flex-col gap-2 lg:flex-row lg:items-stretch">
          <FlowNode title="Airline + OTA sources" sub="11 adapters · Playwright / Scrapy" tone="blue" className="flex-1" />
          <Arrow label="robots + rate limit" />
          <FlowNode title="Raw quotes" sub={`${t.rawQuotes.toLocaleString("en-IN")} rows · dirty strings, sold-out stubs`} tone="white" className="flex-1" />
          <Arrow label="clean" />
          <FlowNode title="Cleaning funnel" sub="parse · dedupe · robust outlier rejection · impute" tone="yellow" className="flex-1" />
          <Arrow label="aggregate" />
          <FlowNode title="Index module" sub="Laspeyres + hedonic · 24 routes × 5 windows" tone="ink" className="flex-1" />
          <Arrow label="publish" />
          <FlowNode title="API + dashboard" sub="/api/v1 · Convex realtime · CPI sub-groups" tone="green" className="flex-1" />
        </div>
      </Panel>

      <Panel kicker="Last run" title="Per-source audit trail" right={<Tag tone="ink">{state.lastRunAt ? new Date(state.lastRunAt).toLocaleString("en-IN") : "seed"}</Tag>}>
        <Table head={["Source", "Type", "Render", "Status", "Quotes", "Req", "Rate", "Crawl-delay", "Blocks", "Note"]}>
          {state.adapters.map((a) => (
            <TR key={a.id}>
              <TD className="font-bold">
                <span className="flex items-center gap-2">
                  <span className="inline-block h-3 w-3 border-2 border-[#0b0b0b]" style={{ background: a.lastRun?.hue ?? "#2b4cff" }} />
                  {a.name}
                </span>
              </TD>
              <TD>{a.kind}</TD>
              <TD className="text-muted-foreground">{a.render}</TD>
              <TD>
                {a.lastRun ? (
                  <Tag tone={STATUS_TONE[a.lastRun.status]}>{a.lastRun.status}</Tag>
                ) : (
                  <Tag tone="paper">idle</Tag>
                )}
              </TD>
              <TD className="text-right">{a.lastRun?.rawQuotes ?? "—"}</TD>
              <TD className="text-right">{a.lastRun?.requests ?? "—"}</TD>
              <TD className="text-right">{a.rateLimit.requestsPerMinute}/min</TD>
              <TD className="text-right">{a.rateLimit.crawlDelaySec}s</TD>
              <TD className="text-right">{a.lastRun?.blockEvents ?? 0}</TD>
              <TD className="max-w-[280px] text-muted-foreground">{a.lastRun?.notes ?? "—"}</TD>
            </TR>
          ))}
        </Table>
      </Panel>

      <div className="grid gap-4 xl:grid-cols-3">
        <Panel kicker="Share of today's collection" title="Where the quotes come from">
          <div className="space-y-2">
            {state.adapters.map((a) => (
              <div key={a.id}>
                <div className="mb-1 flex items-center justify-between">
                  <span className="neo-mono text-[10px] font-bold">{a.name}</span>
                  <span className="neo-mono text-[10px] text-muted-foreground">
                    {a.lastRun?.rawQuotes ?? 0}
                  </span>
                </div>
                <Bar value={a.lastRun?.rawQuotes ?? 0} max={totalQuotes} tone={a.kind === "airline" ? "blue" : "violet"} height={12} />
              </div>
            ))}
          </div>
        </Panel>

        <Panel kicker="Policy, not vibes" title="Ethical collection safeguards">
          <Table head={["Rule", "Implementation"]}>
            <TR>
              <TD className="font-bold">robots.txt</TD>
              <TD className="text-muted-foreground">Fetched and parsed per host before the first request, re-checked on every run; disallowed paths never requested.</TD>
            </TR>
            <TR>
              <TD className="font-bold">Rate limiting</TD>
              <TD className="text-muted-foreground">Token bucket per host, 3–6 requests/min, crawl-delay honoured, 30% jitter, concurrency 1.</TD>
            </TR>
            <TR>
              <TD className="font-bold">CAPTCHAs</TD>
              <TD className="text-muted-foreground">Never solved or bypassed. A challenge is logged as a blocked observation and the cell is imputed from the carrier's own fare index.</TD>
            </TR>
            <TR>
              <TD className="font-bold">Identity</TD>
              <TD className="text-muted-foreground">Descriptive User-Agent with a contact URL; no login, no cookie reuse across users, no purchase flow touched.</TD>
            </TR>
            <TR>
              <TD className="font-bold">Data</TD>
              <TD className="text-muted-foreground">Publicly displayed fares only. No PII, no seat selection, no baggage bypass.</TD>
            </TR>
            <TR>
              <TD className="font-bold">Retries</TD>
              <TD className="text-muted-foreground">Max 3 with 5s / 20s / 60s backoff; repeated failures downgrade the source instead of hammering it.</TD>
            </TR>
          </Table>
        </Panel>

        <Panel kicker="Adapter registry" title="How a source is scraped">
          {state.adapters.slice(0, 4).map((a) => (
            <div key={a.id} className="neo-2 mb-3 bg-white p-3">
              <div className="flex items-center justify-between">
                <p className="text-xs font-extrabold uppercase">{a.name}</p>
                <Tag tone={a.kind === "airline" ? "blue" : "violet"}>{a.kind}</Tag>
              </div>
              <p className="neo-mono mt-1 break-all text-[10px] text-muted-foreground">{a.endpoint}</p>
              <p className="neo-mono mt-1 text-[10px] text-muted-foreground">
                module <span className="font-bold text-[#0b0b0b]">{a.module}</span> · render{" "}
                {a.render} · strategy {a.antiBot.strategy}
              </p>
              <pre className="neo-2 neo-mono mt-2 overflow-x-auto bg-[#f2efe6] p-2 text-[9.5px] leading-4">
{Object.entries(a.selectors)
  .slice(0, 5)
  .map(([k, v]) => `${k.padEnd(15)} ${v}`)
  .join("\n")}
              </pre>
            </div>
          ))}
          <KeyVal k="Collection mode" v="Deterministic seed + live adapters" />
          <KeyVal k="Runs recorded" v={state.runs} />
          <KeyVal k="Blocked this run" v={t.blocked} />
          <KeyVal k="HTTP errors" v={t.httpErrors} />
          <Label>Observation history</Label>
          <div className="space-y-1">
            {state.history.slice(-6).map((h) => (
              <div key={h.date} className="flex items-center justify-between border-b-2 border-[#0b0b0b]/12 py-1">
                <span className="neo-mono text-[10px]">{h.date}</span>
                <span className="neo-mono text-[10px] font-bold">APIx {h.index.toFixed(2)}</span>
                <span className="neo-mono text-[10px] text-muted-foreground">{h.quotes.toLocaleString("en-IN")} quotes</span>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      {runs.length === 0 && (
        <p className="neo-mono text-[10px] text-muted-foreground">
          No collection recorded yet for epoch {state.epoch} — press “Run pipeline” to sweep all 11
          sources.
        </p>
      )}
    </div>
  );
}
