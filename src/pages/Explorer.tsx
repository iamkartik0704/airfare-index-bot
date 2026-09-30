import { useApi } from "@/hooks/useApi";
import { useState } from "react";
import { Bar, Delta, KeyVal, Label, Loading, Panel, Stat, Table, TD, TR, Tag, Btn } from "@/components/neo";

export default function Explorer() {
  const [routeId, setRouteId] = useState("DEL-BOM");
  const [offset, setOffset] = useState(0);
  const method = useApi("methodology");
  const ex = useApi("explorer", { routeId, offsetDays: offset });

  if (!method || !ex) return <Loading label="Replaying a collection" />;

  const r = ex.report;
  const funnel = [
    { label: "Raw quotes rendered", value: r.rawCount, tone: "ink" as const },
    { label: "Dropped · sold out", value: r.droppedSoldOut, tone: "violet" as const },
    { label: "Dropped · cancelled", value: r.droppedCancelled, tone: "violet" as const },
    { label: "Dropped · duplicate", value: r.droppedDuplicate, tone: "yellow" as const },
    { label: "Dropped · outlier", value: r.droppedOutlier, tone: "red" as const },
    { label: "Dropped · unparseable", value: r.droppedInvalid, tone: "red" as const },
    { label: "Imputed (blocked cell)", value: r.imputedCount, tone: "green" as const },
    { label: "Clean quotes kept", value: r.keptCount, tone: "blue" as const },
  ];
  const maxFunnel = Math.max(...funnel.map((f) => f.value), 1);

  return (
    <div className="neo-in space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="neo-mono text-[10px] font-bold uppercase tracking-[0.24em] text-muted-foreground">
            Data quality, inspectable
          </p>
          <h1 className="neo-display mt-1 text-4xl md:text-5xl">Raw → cleaned</h1>
        </div>
        <div className="flex flex-wrap items-end gap-2">
          <label className="neo-mono text-[10px] font-bold uppercase tracking-[0.14em]">
            City-pair
            <select
              value={routeId}
              onChange={(e) => setRouteId(e.target.value)}
              className="neo-2 neo-shadow-xs mt-1 block bg-white px-2 py-1.5 text-xs font-bold"
            >
              {method.routes.map((rt) => (
                <option key={rt.id} value={rt.id}>
                  {rt.id}
                </option>
              ))}
            </select>
          </label>
          <label className="neo-mono text-[10px] font-bold uppercase tracking-[0.14em]">
            Observation date
            <select
              value={offset}
              onChange={(e) => setOffset(Number(e.target.value))}
              className="neo-2 neo-shadow-xs mt-1 block bg-white px-2 py-1.5 text-xs font-bold"
            >
              <option value={0}>Today</option>
              <option value={1}>Yesterday</option>
              <option value={7}>7 days ago</option>
              <option value={30}>30 days ago</option>
            </select>
          </label>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Stat label="Raw quotes (T+7 cell)" value={r.rawCount} hint={`${ex.date} · ${ex.route.origin}→${ex.route.destination}, ${ex.route.distanceKm} km`} tone="blue" />
        <Stat label="Kept after cleaning" value={r.keptCount} hint={`Coverage ${r.coverage.toFixed(1)}%`} tone="green" />
        <Stat label="Median all-in fare" value={`₹${r.medianTotal.toLocaleString("en-IN")}`} hint={`MAD ₹${r.madTotal.toLocaleString("en-IN")} · robust σ used for outlier rejection`} tone="yellow" />
        <Stat label="Cells imputed" value={r.imputedCount} hint="Anti-bot blocks filled from the carrier's fare index and flagged" />
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        <Panel kicker="Cleaning funnel" title="What the pipeline did" className="xl:col-span-2">
          <div className="space-y-2">
            {funnel.map((f) => (
              <div key={f.label}>
                <div className="mb-1 flex items-center justify-between">
                  <span className="neo-mono text-[10px] font-bold uppercase tracking-[0.1em]">{f.label}</span>
                  <span className="neo-mono text-[10px] font-bold">{f.value.toLocaleString("en-IN")}</span>
                </div>
                <Bar value={f.value} max={maxFunnel} tone={f.tone} height={16} />
              </div>
            ))}
          </div>
          <div className="mt-4 grid gap-2 sm:grid-cols-2">
            <div className="neo-2 bg-white p-3">
              <p className="neo-mono text-[10px] font-bold uppercase tracking-[0.14em] text-muted-foreground">
                Channel split of kept quotes
              </p>
              <div className="mt-2 flex gap-2">
                <Tag tone="blue">Airline direct {r.byChannel.airline}</Tag>
                <Tag tone="violet">OTA {r.byChannel.ota}</Tag>
              </div>
            </div>
            <div className="neo-2 bg-white p-3">
              <p className="neo-mono text-[10px] font-bold uppercase tracking-[0.14em] text-muted-foreground">
                Route-level price
              </p>
              <p className="neo-display text-2xl">₹{ex.routeFare.toLocaleString("en-IN")}</p>
              <p className="neo-mono text-[10px] text-muted-foreground">
                booking-curve weighted, weight {ex.route.weight.toFixed(2)}%
              </p>
            </div>
          </div>
        </Panel>

        <div className="space-y-4">
          <Panel kicker="Price surface" title="Same sector, five windows">
            <Table head={["Window", "Fare", "vs T+7"]}>
              {ex.byLead.map((l) => (
                <TR key={l.leadTime}>
                  <TD className="font-bold">T+{l.leadTime}</TD>
                  <TD className="text-right">₹{l.fare.toLocaleString("en-IN")}</TD>
                  <TD className="text-right">
                    <Delta value={l.premiumPct} />
                  </TD>
                </TR>
              ))}
            </Table>
            <Label>By carrier (T+7)</Label>
            {ex.carriers.map((c) => (
              <div key={c.carrier} className="flex items-center justify-between border-b-2 border-[#0b0b0b]/12 py-1">
                <span className="neo-mono text-[10px] font-bold">{c.carrier}</span>
                <span className="neo-mono text-[11px]">₹{c.price.toLocaleString("en-IN")}</span>
              </div>
            ))}
          </Panel>

          <Panel kicker="Decomposition" title="Where a rupee goes">
            <Table head={["Component", "₹"]}>
              {ex.cleanedSample.slice(0, 6).map((q) => (
                <TR key={q.id}>
                  <TD className="font-bold">
                    {q.carrier} · {q.fareClass}
                  </TD>
                  <TD className="text-right">
                    <span className="neo-mono text-[10px]">
                      {q.baseFare} + {q.taxes}
                      {q.convenienceFee ? ` + ${q.convenienceFee} fee` : ""} ={" "}
                      <strong>{q.totalFare}</strong>
                    </span>
                  </TD>
                </TR>
              ))}
            </Table>
            <div className="mt-2">
              <KeyVal k="Base fare" v="Carrier tariff" />
              <KeyVal k="Taxes" v="12% GST + passenger fee + UDF" />
              <KeyVal k="Convenience fee" v="OTA only, ₹35–55" />
            </div>
          </Panel>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <Panel kicker="Before" title="Raw quotes, exactly as rendered">
          <Table head={["Source", "Carrier", "Class", "Fare text", "Tax text", "Seats", "Flags"]}>
            {ex.rawSample.slice(0, 12).map((q) => (
              <TR key={q.id} className={q.soldOut ? "opacity-45" : ""}>
                <TD>{q.sourceId}</TD>
                <TD className="font-bold">{q.carrier}</TD>
                <TD>{q.fareClass}</TD>
                <TD>{q.fareText}</TD>
                <TD className="text-muted-foreground">{q.taxText}</TD>
                <TD className="text-right">{q.seatsLeft}</TD>
                <TD>
                  {q.soldOut ? (
                    <Tag tone="red">sold out</Tag>
                  ) : q.isCancelled ? (
                    <Tag tone="red">cancelled</Tag>
                  ) : q.seatsLeft <= 4 ? (
                    <Tag tone="yellow">scarce</Tag>
                  ) : (
                    <Tag tone="green">ok</Tag>
                  )}
                </TD>
              </TR>
            ))}
          </Table>
        </Panel>

        <Panel kicker="After" title="Clean, typed and decomposed" right={
          <Btn tone="ink" className="px-2 py-1 text-[10px] uppercase font-bold" onClick={() => {
            const csv = ["ID,Source,Carrier,Class,Base,Taxes,Fee,Total,Quality,Flags"];
            ex.cleanedSample.forEach((q: any) => csv.push(`${q.id},${q.sourceId},${q.carrier},${q.fareClass},${q.baseFare},${q.taxes},${q.convenienceFee || 0},${q.totalFare},${q.quality.toFixed(2)},"${q.flags.join(", ")}"`));
            const blob = new Blob([csv.join("\n")], { type: "text/csv" });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `safar_cleaned_${ex.route.origin}_${ex.route.destination}.csv`;
            a.click();
          }}>Export CSV</Btn>
        }>
          <Table head={["Source", "Carrier", "Class", "Base", "Taxes", "Fee", "Total", "Quality", "Flags"]}>
            {ex.cleanedSample.slice(0, 12).map((q) => (
              <TR key={q.id} className={q.imputed ? "opacity-60" : ""}>
                <TD>{q.sourceId}</TD>
                <TD className="font-bold">{q.carrier}</TD>
                <TD>{q.fareClass}</TD>
                <TD className="text-right">{q.baseFare}</TD>
                <TD className="text-right">{q.taxes}</TD>
                <TD className="text-right">{q.convenienceFee || "—"}</TD>
                <TD className="text-right font-bold">{q.totalFare}</TD>
                <TD className="text-right">{q.quality.toFixed(2)}</TD>
                <TD className="text-muted-foreground">{q.flags.join(", ") || "—"}</TD>
              </TR>
            ))}
          </Table>
        </Panel>
      </div>
    </div>
  );
}
