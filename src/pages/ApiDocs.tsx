import { useQuery } from "convex/react";
import { api } from "@/convex/_generated/api";
import { KeyVal, Label, Loading, Panel, Table, TD, TR, Tag } from "@/components/neo";

const ENDPOINTS = [
  {
    method: "GET",
    path: "/api/v1/health",
    what: "Liveness, basket size and reference period.",
    sample: '{ "status": "ok", "basket": { "routes": 24, "sources": 11 } }',
  },
  {
    method: "GET",
    path: "/api/v1/index/latest",
    what: "Headline APIx with day-on-day and year-on-year change.",
    sample: '{ "date": "2026-09-30", "value": 102.97, "change": { "yoy": 3.05 } }',
  },
  {
    method: "GET",
    path: "/api/v1/index/series?freq=daily|weekly|monthly&days=90",
    what: "Time series at any of the three release frequencies.",
    sample: '{ "frequency": "monthly", "points": [ { "period": "2026-09", "value": 103.8 } ] }',
  },
  {
    method: "GET",
    path: "/api/v1/basket",
    what: "City-pair weights, current per-route indices and advance-purchase sub-indices.",
    sample: '{ "routes": [ { "id": "DEL-BOM", "weightPct": 11.44 } ] }',
  },
  {
    method: "GET",
    path: "/api/v1/backtest",
    what: "Validation against the DGCA monthly average fare, with metrics.",
    sample: '{ "metrics": { "pearson": 0.97, "mapePct": 4.09 } }',
  },
];

export default function ApiDocs() {
  const releases = useQuery(api.apix.releases);
  const base = (import.meta.env.VITE_CONVEX_URL as string | undefined)?.replace(/\/$/, "") ?? "https://<deployment>.convex.cloud";

  return (
    <div className="neo-in space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="neo-mono text-[10px] font-bold uppercase tracking-[0.24em] text-muted-foreground">
            For NSO / RBI / academia
          </p>
          <h1 className="neo-display mt-1 text-4xl md:text-5xl">Public API</h1>
        </div>
        <div className="flex flex-wrap gap-2">
          <Tag tone="ink">REST · JSON · CORS open</Tag>
          <Tag tone="yellow">x-api-key auth</Tag>
          <Tag tone="green">v1 · stable</Tag>
        </div>
      </div>

      <Panel kicker="Authentication" title="One header">
        <p className="text-sm leading-6">
          Every request except <code className="neo-mono bg-[#e6e1d4] px-1">/api/v1/health</code>{" "}
          requires an API key issued by the SAFAR registrar. Keys are stored hashed, scoped per
          organisation and logged with a 30-day audit trail. The prototype ships one demo key.
        </p>
        <div className="neo-2 neo-shadow-sm mt-3 bg-[#0b0b0b] p-3">
          <p className="neo-mono text-[11px] text-[#ffd400]">x-api-key: safar-demo-26056</p>
        </div>
        <div className="mt-3">
          <KeyVal k="Scopes" v="index:read · routes:read · backtest:read" />
          <KeyVal k="Rate limit" v="600 req/min per key, burst 50" />
          <KeyVal k="Release cadence" v="Daily 06:30 IST · weekly Mon · monthly 1st working day" />
          <KeyVal k="Provisional window" v="60 days, then frozen with a revision note" />
        </div>
      </Panel>

      <Panel kicker="Reference" title="Endpoints">
        <Table head={["Method", "Path", "Returns"]}>
          {ENDPOINTS.map((e) => (
            <TR key={e.path}>
              <TD>
                <Tag tone="blue">{e.method}</Tag>
              </TD>
              <TD className="max-w-[320px] break-all font-bold">{e.path}</TD>
              <TD className="text-muted-foreground">{e.what}</TD>
            </TR>
          ))}
        </Table>
      </Panel>

      <Panel kicker="Try it" title="Copy-paste examples">
        <div className="space-y-3">
          {ENDPOINTS.slice(1).map((e) => (
            <div key={e.path}>
              <p className="neo-mono mb-1 text-[10px] font-bold uppercase tracking-[0.14em] text-muted-foreground">
                {e.path}
              </p>
              <pre className="neo-2 neo-mono overflow-x-auto bg-[#0b0b0b] p-3 text-[11px] leading-5 text-[#f2efe6]">
{`curl -s "${base}${e.path}" \\
  -H "x-api-key: safar-demo-26056"`}
              </pre>
              <pre className="neo-2 neo-mono mt-1 overflow-x-auto bg-[#e6e1d4] p-3 text-[11px] leading-5">
{e.sample}
              </pre>
            </div>
          ))}
        </div>
      </Panel>

      <div className="grid gap-4 xl:grid-cols-2">
        <Panel kicker="Delivery" title="How NSO would consume it">
          <ul className="space-y-2 text-sm leading-6">
            <li>• <strong>Pull</strong> the monthly sub-index at release, or subscribe to the webhook for a new period.</li>
            <li>• <strong>Validate</strong> against the DGCA monthly average fare with the shipped back-test methodology.</li>
            <li>• <strong>Weight</strong> into the Transport &amp; Communication sub-group using published city-pair weights.</li>
            <li>• <strong>Explain</strong> movements with the driver decomposition — fuel, rupee, demand, calendar.</li>
          </ul>
          <Label>Suggested integration</Label>
          <pre className="neo-2 neo-mono overflow-x-auto bg-[#0b0b0b] p-3 text-[11px] leading-5 text-[#f2efe6]">
{`GET /api/v1/index/series?freq=monthly&days=400
→ [{ period, value, change, yoy, avgFare }]

weight = Σ ( city-pair share × route index )
publish as PSI-AIR sub-group within T&C`}
          </pre>
        </Panel>

        <Panel kicker="Release ledger" title="What has been published">
          {releases === undefined ? (
            <Loading label="Reading ledger" />
          ) : releases.length === 0 ? (
            <div className="neo-dotted border-[3px] border-dashed border-[#0b0b0b]/40 p-4">
              <p className="neo-mono text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
                No releases recorded in this environment yet.
              </p>
              <p className="mt-2 text-sm leading-6">
                In production the scheduler writes one ledger row per period per frequency with the
                published value, the timestamp and the delivery channels — the immutable record an
                NSO audit would ask for.
              </p>
            </div>
          ) : (
            <Table head={["Period", "Freq", "Value", "Published", "Channels"]}>
              {releases.map((r) => (
                <TR key={r._id}>
                  <TD className="font-bold">{r.period}</TD>
                  <TD>{r.frequency}</TD>
                  <TD className="text-right">{r.value.toFixed(2)}</TD>
                  <TD>{new Date(r.publishedAt).toLocaleString("en-IN")}</TD>
                  <TD className="text-muted-foreground">{r.channels.join(", ")}</TD>
                </TR>
              ))}
            </Table>
          )}
        </Panel>
      </div>
    </div>
  );
}
