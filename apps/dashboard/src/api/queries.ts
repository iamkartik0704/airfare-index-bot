import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { apiGet, type QueryParams } from "./client";
import type {
  BacktestOut,
  BenchmarkOut,
  CarrierAnalysis,
  ChannelAnalysis,
  FareLineage,
  FareOut,
  FunnelOut,
  Headline,
  HealthBucket,
  HeatmapOut,
  IndexScope,
  IndexSeries,
  JobOut,
  LeadTimeOut,
  Lineage,
  Methodology,
  Page,
  RouteSummary,
  RouteTrends,
  SubIndices,
  SweepOut,
  SystemHealth,
} from "./types";

/**
 * One React Query hook per read-only endpoint. Hooks return the API payload
 * untouched — the dashboard formats, it never recomputes.
 */

const MIN = 60_000;

function get<T>(path: string, params?: QueryParams) {
  return ({ signal }: { signal: AbortSignal }) => apiGet<T>(path, params, signal);
}

// ------------------------------------------------------------------ index
export function useHeadline() {
  return useQuery({ queryKey: ["index", "latest"], queryFn: get<Headline>("/index/latest"), staleTime: MIN });
}

export interface SeriesParams {
  start_date?: string;
  end_date?: string;
  scope?: IndexScope;
  key?: string;
}

export function useIndexSeries(frequency: "daily" | "weekly" | "monthly", params: SeriesParams = {}, enabled = true) {
  const p = { scope: "HEADLINE", ...params } as QueryParams;
  return useQuery({
    queryKey: ["index", frequency, p],
    queryFn: get<IndexSeries>(`/index/${frequency}`, p),
    staleTime: 5 * MIN,
    placeholderData: keepPreviousData,
    enabled,
  });
}

export function useSubIndices(date?: string) {
  return useQuery({
    queryKey: ["index", "sub-indices", date ?? null],
    queryFn: get<SubIndices>("/index/sub-indices", { date }),
    staleTime: 5 * MIN,
  });
}

export function useLineage(date: string | undefined) {
  return useQuery({
    queryKey: ["index", "lineage", date],
    queryFn: get<Lineage>(`/index/daily/${date}/lineage`),
    enabled: Boolean(date),
    staleTime: 10 * MIN,
  });
}

// ------------------------------------------------------------------ routes
export function useRoutes() {
  return useQuery({ queryKey: ["routes"], queryFn: get<RouteSummary[]>("/routes"), staleTime: 5 * MIN });
}

export function useRouteTrends(code: string | undefined, params: { start_date?: string; end_date?: string } = {}) {
  return useQuery({
    queryKey: ["routes", code, "trends", params],
    queryFn: get<RouteTrends>(`/routes/${code}/trends`, params),
    enabled: Boolean(code),
    staleTime: 5 * MIN,
  });
}

// ------------------------------------------------------------------ analytics
export function useLeadTime(params: { date?: string; route?: string }) {
  return useQuery({
    queryKey: ["analytics", "lead-time", params],
    queryFn: get<LeadTimeOut>("/analytics/lead-time", params),
    staleTime: 5 * MIN,
    placeholderData: keepPreviousData,
  });
}

export function useHeatmap(frequency: "WEEKLY" | "MONTHLY", periods: number) {
  return useQuery({
    queryKey: ["analytics", "heatmap", frequency, periods],
    queryFn: get<HeatmapOut>("/analytics/heatmap", { frequency, periods }),
    staleTime: 5 * MIN,
    placeholderData: keepPreviousData,
  });
}

export function useCarriers(params: { date?: string; route?: string }) {
  return useQuery({
    queryKey: ["analytics", "carriers", params],
    queryFn: get<CarrierAnalysis>("/analytics/carriers", params),
    staleTime: 5 * MIN,
    placeholderData: keepPreviousData,
  });
}

export function useChannels(date?: string) {
  return useQuery({
    queryKey: ["analytics", "channels", date ?? null],
    queryFn: get<ChannelAnalysis>("/analytics/channels", { date }),
    staleTime: 5 * MIN,
    placeholderData: keepPreviousData,
  });
}

export function useFunnel(params: { date?: string; route?: string }) {
  return useQuery({
    queryKey: ["analytics", "funnel", params],
    queryFn: get<FunnelOut>("/analytics/funnel", params),
    staleTime: 5 * MIN,
    placeholderData: keepPreviousData,
  });
}

// ------------------------------------------------------------------ fares
export interface FareFilters {
  route?: string;
  observation_date?: string;
  travel_date?: string;
  purchase_window?: number;
  carrier?: string;
  source?: string;
  quality_flag?: string;
  canonical_only?: boolean;
  limit: number;
  offset: number;
}

export function useFares(filters: FareFilters) {
  return useQuery({
    queryKey: ["fares", filters],
    queryFn: get<Page<FareOut>>("/fares", filters as unknown as QueryParams),
    staleTime: MIN,
    placeholderData: keepPreviousData,
  });
}

export function useFareLineage(id: number | null) {
  return useQuery({
    queryKey: ["fares", "lineage", id],
    queryFn: get<FareLineage>(`/fares/${id}`),
    enabled: id !== null,
    staleTime: 30 * MIN,
  });
}

// ------------------------------------------------------------------ system / jobs
export function useSystemHealth() {
  return useQuery({
    queryKey: ["system", "health"],
    queryFn: get<SystemHealth>("/system/health"),
    staleTime: 15_000,
    refetchInterval: 30_000,
  });
}

export function useSourceHealth(id: string | null, hours = 48) {
  return useQuery({
    queryKey: ["system", "sources", id, "health", hours],
    queryFn: get<HealthBucket[]>(`/system/sources/${id}/health`, { hours }),
    enabled: id !== null,
    staleTime: MIN,
  });
}

export function useJobs(params: { status?: string; source?: string; sweep_id?: string; limit?: number; offset?: number }) {
  return useQuery({
    queryKey: ["jobs", params],
    queryFn: get<Page<JobOut>>("/jobs", params),
    staleTime: 30_000,
    refetchInterval: 60_000,
    placeholderData: keepPreviousData,
  });
}

export function useSweeps(params: { status?: string; limit?: number; offset?: number }) {
  return useQuery({
    queryKey: ["sweeps", params],
    queryFn: get<Page<SweepOut>>("/sweeps", params),
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
}

// ------------------------------------------------------------------ validation / methodology
export function useBacktest() {
  return useQuery({ queryKey: ["backtests", "latest"], queryFn: get<BacktestOut>("/backtests/latest"), staleTime: 10 * MIN });
}

export function useBenchmarks() {
  return useQuery({ queryKey: ["benchmarks"], queryFn: get<BenchmarkOut[]>("/benchmarks"), staleTime: 30 * MIN });
}

export function useMethodology() {
  return useQuery({ queryKey: ["methodology"], queryFn: get<Methodology>("/methodology"), staleTime: 30 * MIN });
}
