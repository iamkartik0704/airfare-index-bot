import { useState, useEffect } from "react";

const API_BASE = "http://localhost:8001/api";

const cache: Record<string, any> = {
  'periodicSeries{}': Array.from({ length: 12 }, (_, i) => ({
    period: `2026-${(i + 1).toString().padStart(2, '0')}`,
    label: `Month ${i+1}`,
    index: 100 + i,
    change: 1.2,
    changeYoy: 5.5
  })),
  'subIndexSeries{}': [
    { key: "T+1", group: "window", label: "Advance purchase · T+1", value: 120, changeYoy: 5, series: [] },
    { key: "T+15", group: "window", label: "Advance purchase · T+15", value: 95, changeYoy: -2, series: [] },
    { key: "North", group: "region", label: "North", value: 105, changeYoy: 3, series: [] }
  ],
  'explorer{}': {
    date: "2026-09-30",
    route: { origin: "DEL", destination: "BOM", distanceKm: 1148, weight: 5.0 },
    routeFare: 4500,
    report: {
      rawCount: 200,
      droppedSoldOut: 10,
      droppedCancelled: 0,
      droppedDuplicate: 5,
      droppedOutlier: 2,
      droppedInvalid: 0,
      imputedCount: 15,
      keptCount: 168,
      coverage: 95.0,
      medianTotal: 4400,
      madTotal: 250,
      byChannel: { airline: 100, ota: 68 }
    },
    byLead: [
      { leadTime: 1, fare: 6500, premiumPct: 20 },
      { leadTime: 7, fare: 4500, premiumPct: 0 }
    ],
    carriers: [
      { carrier: "6E", price: 4400 },
      { carrier: "UK", price: 5000 }
    ],
    rawSample: [
      { id: "1", sourceId: "indigo", carrier: "6E", fareClass: "Economy", fareText: "4000", taxText: "400", seatsLeft: 5, soldOut: false, isCancelled: false }
    ],
    cleanedSample: [
      { id: "1", sourceId: "indigo", carrier: "6E", fareClass: "Economy", baseFare: 4000, taxes: 400, convenienceFee: 0, totalFare: 4400, quality: 1.0, flags: [], imputed: false }
    ]
  }
};

export function useApi(queryKey: string, params: any = {}) {
  const cacheKey = queryKey + JSON.stringify(params);
  const [data, setData] = useState<any>(cache[cacheKey] !== undefined ? cache[cacheKey] : undefined);
  
  useEffect(() => {
    async function fetchData() {
      if (cache[cacheKey] !== undefined) {
        return; // already cached
      }
      try {
        if (queryKey === "headline") {
          // Fetch from /api/routes/heatmap and /api/index
          const [heatmapRes, indexRes] = await Promise.all([
            fetch(`${API_BASE}/routes/heatmap`),
            fetch(`${API_BASE}/index`)
          ]);
          const heatmapData = await heatmapRes.json();
          const indexPointsData = await indexRes.json();
          
          const heatmap = heatmapData.data;
          const indexPoints = indexPointsData.data;
          const isSimulated = heatmapData.data_origin === "simulated" || indexPointsData.data_origin === "simulated";
          
          const latest = indexPoints[indexPoints.length - 1] || {};
          const prevDay = indexPoints[indexPoints.length - 2] || {};
          
          const result = {
            routeRows: heatmap.map((h: any) => ({
              id: h.route,
              origin: h.route.split('-')[0],
              destination: h.route.split('-')[1],
              weight: 5.0,
              fare: h.avg_fare,
              change: 1.2
            })),
            epoch: 2,
            sources: 2,
            routes: 24,
            windows: 5,
            quotesPerSweep: latest.observations || 5000,
            index: latest.value || 100,
            momPct: 2.1,
            rawToday: latest.nominal || 100,
            yoy: 4.5,
            avgFare: latest.avg_fare || 4500,
            lastRunAt: new Date().toISOString(),
            wow: 0.5,
            dod: latest.value && prevDay.value ? ((latest.value / prevDay.value) - 1) * 100 : 0,
            dataOrigin: indexPointsData.data_origin
          };
          cache[cacheKey] = result;
          setData(result);
        } 
        else if (queryKey === "dailySeries") {
          const res = await fetch(`${API_BASE}/index`);
          const json = await res.json();
          const indexPoints = json.data;
          const result = indexPoints.map((p: any) => ({
            date: p.date,
            index7d: p.value,
            index: p.nominal
          }));
          cache[cacheKey] = result;
          setData(result);
        }
        else if (queryKey === "periodicSeries") {
          // Mock monthly for now
          const result = Array.from({ length: 12 }, (_, i) => ({
            period: `2026-${(i + 1).toString().padStart(2, '0')}`,
            label: `Month ${i+1}`,
            index: 100 + i,
            change: 1.2,
            changeYoy: 5.5
          }));
          cache[cacheKey] = result;
          setData(result);
        }
        else if (queryKey === "subIndexSeries") {
          // Mock sub-indices
          const result = [
            { key: "T+1", group: "window", label: "Advance purchase · T+1", value: 120, changeYoy: 5, series: [] },
            { key: "T+15", group: "window", label: "Advance purchase · T+15", value: 95, changeYoy: -2, series: [] },
            { key: "North", group: "region", label: "North", value: 105, changeYoy: 3, series: [] }
          ];
          cache[cacheKey] = result;
          setData(result);
        }
        else if (queryKey === "pipelineState") {
          const res = await fetch(`${API_BASE}/pipelineState`);
          const json = await res.json();
          cache[cacheKey] = json;
          setData(json);
        }
        else if (queryKey === "elasticity") {
          const res = await fetch(`${API_BASE}/elasticity`);
          const json = await res.json();
          const ePoints = json.data;
          const result = {
            points: ePoints.map((p: any) => ({
              leadTime: p.lead_days,
              index: p.avg_fare,
              premiumPct: 5,
              elasticity: -0.1
            })),
            optimalLead: 15,
            savingPct: 20,
            lateRisePct: 5,
            dataOrigin: json.data_origin
          };
          cache[cacheKey] = result;
          setData(result);
        }
        else if (queryKey === "heatmap") {
          const res = await fetch(`${API_BASE}/routes/heatmap`);
          const json = await res.json();
          const result = json.data.map((h: any) => ({
            routeId: h.route,
            period: "Sep 2026",
            change: 1.2
          }));
          cache[cacheKey] = result;
          setData(result);
        }
        else if (queryKey === "routeContributions") {
          const res = await fetch(`${API_BASE}/routes/heatmap`);
          const json = await res.json();
          const result = json.data.map((h: any) => ({
            routeId: h.route,
            contribution: 1.5,
            weight: 5.0,
            priceChange: 2.1
          }));
          cache[cacheKey] = result;
          setData(result);
        }
        else if (queryKey === "channelAnalysis") {
          const res = await fetch(`${API_BASE}/channelAnalysis`);
          const json = await res.json();
          cache[cacheKey] = json.data;
          setData(json.data);
        }
        else if (queryKey === "methodology") {
          const res = await fetch(`${API_BASE}/methodology`);
          const json = await res.json();
          cache[cacheKey] = json;
          setData(json);
        }
        else if (queryKey === "validation") {
          const res = await fetch(`${API_BASE}/validation`);
          const json = await res.json();
          cache[cacheKey] = json;
          setData(json);
        }
        else if (queryKey === "drivers") {
          const res = await fetch(`${API_BASE}/drivers`);
          const json = await res.json();
          cache[cacheKey] = json;
          setData(json);
        }
        else if (queryKey === "releases") {
          const res = await fetch(`${API_BASE}/releases`);
          const json = await res.json();
          cache[cacheKey] = json;
          setData(json);
        }
        else if (queryKey === "explorer") {
          const result = {
            date: "2026-09-30",
            route: { origin: "DEL", destination: "BOM", distanceKm: 1148, weight: 5.0 },
            routeFare: 4500,
            report: {
              rawCount: 200,
              droppedSoldOut: 10,
              droppedCancelled: 0,
              droppedDuplicate: 5,
              droppedOutlier: 2,
              droppedInvalid: 0,
              imputedCount: 15,
              keptCount: 168,
              coverage: 95.0,
              medianTotal: 4400,
              madTotal: 250,
              byChannel: { airline: 100, ota: 68 }
            },
            byLead: [
              { leadTime: 1, fare: 6500, premiumPct: 20 },
              { leadTime: 7, fare: 4500, premiumPct: 0 }
            ],
            carriers: [
              { carrier: "6E", price: 4400 },
              { carrier: "UK", price: 5000 }
            ],
            rawSample: [
              { id: "1", sourceId: "indigo", carrier: "6E", fareClass: "Economy", fareText: "4000", taxText: "400", seatsLeft: 5, soldOut: false, isCancelled: false }
            ],
            cleanedSample: [
              { id: "1", sourceId: "indigo", carrier: "6E", fareClass: "Economy", baseFare: 4000, taxes: 400, convenienceFee: 0, totalFare: 4400, quality: 1.0, flags: [], imputed: false }
            ]
          };
          cache[cacheKey] = result;
          setData(result);
        }
      } catch (err) {
        console.error("API error", err);
      }
    }
    fetchData();
  }, [queryKey, JSON.stringify(params)]);

  return data;
}
