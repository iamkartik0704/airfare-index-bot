/**
 * TypeScript mirror of the FastAPI response schemas
 * (apps/api/schemas/common.py, index.py, operations.py).
 *
 * Conventions:
 *  - `Decimal` fields are serialised by Pydantic as JSON strings ("102.8418");
 *    they are typed `DecimalStr` and converted with `num()` only for display.
 *  - dates are ISO `YYYY-MM-DD`, datetimes ISO-8601 strings, UUIDs strings.
 */

export type DecimalStr = string;
export type ISODate = string;
export type ISODateTime = string;
export type UUID = string;

export type DataOrigin = "live" | "simulated" | "mixed" | "none";

// ------------------------------------------------------------------ enums
export type SourceKind = "AIRLINE" | "OTA" | "SIMULATED";
export type SourceStatus = "ACTIVE" | "DEGRADED" | "BLOCKED" | "DISABLED";
export type JobStatus = "PENDING" | "RUNNING" | "RETRY" | "SUCCESS" | "FAILED" | "SKIPPED";
export type SweepTrigger = "SCHEDULED" | "MANUAL" | "BACKFILL";
export type SweepStatus = "RUNNING" | "COMPLETED" | "COMPLETED_WITH_ERRORS";
export type AvailabilityStatus = "AVAILABLE" | "SOLD_OUT" | "CANCELLED";
export type QualityFlag = "VALID" | "OUTLIER" | "DUPLICATE" | "INVALID";
export type Cabin = "ECONOMY" | "PREMIUM_ECONOMY" | "BUSINESS";
export type IndexFrequency = "DAILY" | "WEEKLY" | "MONTHLY";
export type IndexScope = "HEADLINE" | "WINDOW" | "ROUTE" | "REGION";

// ------------------------------------------------------------------ common
export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface ErrorBody {
  code: string;
  message: string;
  details: Record<string, unknown>;
  request_id: string | null;
}

export interface ErrorResponse {
  error: ErrorBody;
}

// ------------------------------------------------------------------ index
export interface IndexPoint {
  period_start: ISODate;
  period_end: ISODate;
  value: DecimalStr;
  nominal_value: DecimalStr;
  rolling_value: DecimalStr | null;
  avg_fare: DecimalStr;
  observation_count: number;
  coverage_pct: DecimalStr;
  imputed_share: DecimalStr;
  is_synthetic: boolean;
}

export interface IndexSeries {
  frequency: IndexFrequency;
  scope: IndexScope;
  scope_key: string;
  data_origin: DataOrigin;
  base_period: [ISODate, ISODate] | null;
  items: IndexPoint[];
}

export interface Headline {
  date: ISODate;
  value: DecimalStr;
  nominal_value: DecimalStr;
  rolling_value: DecimalStr;
  avg_fare: DecimalStr;
  change_dod_pct: DecimalStr | null;
  change_wow_pct: DecimalStr | null;
  change_mom_pct: DecimalStr | null;
  coverage_pct: DecimalStr;
  imputed_share: DecimalStr;
  observation_count: number;
  base_period: [ISODate, ISODate] | null;
  computed_at: ISODateTime | null;
  data_origin: DataOrigin;
  /** e.g. {basket_weights: "INDICATIVE", hedonic_factors: "INDICATIVE", hedonic_adjustment: "ON"} */
  methodology_status: Record<string, string>;
}

export interface SubIndex {
  scope: IndexScope;
  scope_key: string;
  value: DecimalStr;
  change_pct: DecimalStr | null;
  avg_fare: DecimalStr;
}

export interface SubIndices {
  date: ISODate;
  data_origin: DataOrigin;
  items: SubIndex[];
}

export interface LineageCell {
  route: string;
  purchase_window: number;
  median_fare: DecimalStr;
  quote_count: number;
  source_count: number;
  imputed: boolean;
  imputed_from_date: ISODate | null;
  is_synthetic: boolean;
}

export interface Lineage {
  date: ISODate;
  index_value: DecimalStr;
  index_run_id: string;
  computed_at: ISODateTime | null;
  parameters: Record<string, unknown>;
  cells: LineageCell[];
  quotes_endpoint: string;
}

export interface RouteSummary {
  code: string;
  origin: string;
  destination: string;
  distance_km: number;
  region: string;
  weight: DecimalStr;
  weight_share_pct: DecimalStr;
  latest_index: DecimalStr | null;
  latest_avg_fare: DecimalStr | null;
  change_mom_pct: DecimalStr | null;
}

export interface LeadTimePoint {
  purchase_window: number;
  fare: DecimalStr;
  premium_pct: DecimalStr;
}

export interface LeadTimeOut {
  date: ISODate;
  route: string | null;
  /** Slope of ln(fare) on ln(days ahead) — a float, not a Decimal. */
  elasticity: number | null;
  cheapest_window: number | null;
  data_origin: DataOrigin;
  points: LeadTimePoint[];
}

export interface RouteTrends {
  route: RouteSummary;
  lead_time: LeadTimeOut;
  history: IndexPoint[];
  data_origin: DataOrigin;
}

// ------------------------------------------------------------------ fares
export interface FareOut {
  id: number;
  source_id: string;
  route: string;
  carrier_code: string;
  flight_number: string;
  fare_class: string;
  fare_family: string | null;
  cabin: Cabin;
  observation_date: ISODate;
  observed_at: ISODateTime;
  travel_date: ISODate;
  purchase_window: number;
  base_fare: DecimalStr | null;
  taxes: DecimalStr | null;
  airport_fees: DecimalStr | null;
  convenience_fee: DecimalStr | null;
  total_fare: DecimalStr | null;
  availability: AvailabilityStatus;
  seats_left: number | null;
  stops: number | null;
  quality_flag: QualityFlag;
  quality_reasons: string[];
  is_canonical: boolean;
  is_synthetic: boolean;
}

export interface FareLineage {
  fare: FareOut;
  raw_payload: Record<string, unknown>;
  parser: string;
  response_id: UUID;
  response_url: string;
  response_status: number;
  response_sha256: string;
  fetched_at: ISODateTime;
  job_id: UUID;
  sweep_id: UUID;
}

export interface FunnelOut {
  observation_date: ISODate;
  route: string | null;
  raw: number;
  normalized: number;
  valid: number;
  outliers: number;
  duplicates: number;
  invalid: number;
  sold_out: number;
  cancelled: number;
  canonical: number;
}

// ------------------------------------------------------------------ analytics
export interface HeatCell {
  route: string;
  region: string;
  period: ISODate;
  value: DecimalStr;
  change_pct: DecimalStr | null;
}

export interface HeatmapOut {
  frequency: string;
  periods: ISODate[];
  data_origin: DataOrigin;
  cells: HeatCell[];
}

export interface CarrierRow {
  carrier_code: string;
  carrier_name: string;
  median_fare: DecimalStr;
  quote_count: number;
  premium_pct: DecimalStr | null;
}

export interface CarrierAnalysis {
  date: ISODate;
  route: string | null;
  data_origin: DataOrigin;
  items: CarrierRow[];
}

export interface ChannelRow {
  route: string;
  direct_median: DecimalStr | null;
  ota_median: DecimalStr | null;
  wedge_pct: DecimalStr | null;
  matched_fares: number;
}

export interface ChannelAnalysis {
  date: ISODate;
  data_origin: DataOrigin;
  items: ChannelRow[];
}

// ------------------------------------------------------------------ system
export interface SourceHealth {
  id: string;
  name: string;
  kind: SourceKind;
  enabled: boolean;
  runnable: boolean;
  is_synthetic: boolean;
  tos_reviewed: boolean;
  status: SourceStatus;
  status_reason: string | null;
  circuit_open_until: ISODateTime | null;
  consecutive_failures: number;
  last_success_at: ISODateTime | null;
  rate_limit_rpm: number;
  crawl_delay_s: number;
  window_hours: number;
  requests: number;
  jobs_succeeded: number;
  jobs_failed: number;
  blocked: number;
  rate_limited: number;
  parse_errors: number;
  robots_denied: number;
  quotes_collected: number;
  success_rate: number | null;
  avg_latency_ms: number | null;
}

export interface HealthBucket {
  bucket_start: ISODateTime;
  requests: number;
  jobs_succeeded: number;
  jobs_failed: number;
  blocked: number;
  parse_errors: number;
  quotes_collected: number;
  status_codes: Record<string, number>;
}

export interface Freshness {
  latest_observation_at: ISODateTime | null;
  latest_observation_date: ISODate | null;
  age_seconds: number | null;
  stale: boolean;
  latest_index_date: ISODate | null;
  latest_index_run_at: ISODateTime | null;
}

export interface SystemHealth {
  status: "ok" | "degraded" | "down" | string;
  database: string;
  freshness: Freshness;
  queue: Record<string, number>;
  sources: SourceHealth[];
}

// ------------------------------------------------------------------ jobs
export interface JobOut {
  id: UUID;
  sweep_id: UUID;
  source_id: string;
  route: string;
  observation_date: ISODate;
  travel_date: ISODate;
  purchase_window: number;
  status: JobStatus;
  attempts: number;
  max_attempts: number;
  items_scraped: number;
  errors_encountered: number;
  last_error_code: string | null;
  last_error_message: string | null;
  started_at: ISODateTime | null;
  completed_at: ISODateTime | null;
}

export interface SweepOut {
  id: UUID;
  slot: string;
  trigger_type: SweepTrigger;
  observation_date: ISODate;
  status: SweepStatus;
  jobs_total: number;
  created_at: ISODateTime;
  completed_at: ISODateTime | null;
  job_counts: Record<string, number>;
}

// ------------------------------------------------------------------ backtest
export interface BacktestPoint {
  granularity: "DAY" | "MONTH" | string;
  period: ISODate;
  apix_avg_fare: DecimalStr;
  apix_index: DecimalStr | null;
  benchmark_avg_fare: DecimalStr;
  abs_pct_error: DecimalStr;
}

/** `metrics` is `dict[str, Any]` server-side; these are the keys it currently carries. */
export interface BacktestMetrics {
  days_covered?: number;
  months_covered?: number;
  daily_mape_pct?: number | string | null;
  monthly_mape_pct?: number | string | null;
  pearson?: number | string | null;
  spearman?: number | string | null;
  directional_accuracy?: number | string | null;
  mean_bias_pct?: number | string | null;
  pearson_target?: number | string | null;
  min_days_required?: number;
  [key: string]: unknown;
}

export interface BacktestOut {
  id: UUID;
  created_at: ISODateTime;
  period_start: ISODate;
  period_end: ISODate;
  days_covered: number;
  benchmark_label: string;
  benchmark_is_synthetic: boolean;
  apix_is_synthetic: boolean;
  metrics: BacktestMetrics;
  verdict: string;
  points: BacktestPoint[];
}

export interface BenchmarkOut {
  period_month: ISODate;
  route_code: string;
  avg_fare: DecimalStr;
  source_label: string;
  source_url: string | null;
  is_synthetic: boolean;
}

// ------------------------------------------------------------------ methodology
export interface BasketRoute {
  code: string;
  region: string;
  distance_km: number;
  weight: DecimalStr | number;
  weight_share_pct: DecimalStr | number;
}

export interface MethodologyBasket {
  version?: string;
  status?: string;
  weights_source?: string;
  routes?: BasketRoute[];
  [key: string]: unknown;
}

export interface FareClassInfo {
  code: string;
  label: string;
  cabin: string;
  quality_factor: DecimalStr | number;
}

export interface MethodologyFareClasses {
  status?: string;
  note?: string;
  classes?: FareClassInfo[];
  [key: string]: unknown;
}

export interface MethodologySource {
  id: string;
  name: string;
  kind: SourceKind | string;
  channel?: string;
  enabled: boolean;
  tos_reviewed: boolean;
  rate_limit_rpm: number;
  crawl_delay_s: number;
  fetch_mode?: string;
  is_synthetic: boolean;
  notes?: string | null;
  [key: string]: unknown;
}

export interface Methodology {
  formula: string;
  description: string[];
  basket: MethodologyBasket;
  fare_classes: MethodologyFareClasses;
  purchase_windows: number[];
  window_weights: Record<string, string>;
  hedonic_adjustment: boolean;
  base_period: [ISODate, ISODate] | null;
  base_period_source: string | null;
  cabins: string[];
  include_connecting: boolean;
  quality_rules: Record<string, unknown>;
  external_dependencies: string[];
  sources: MethodologySource[];
}
