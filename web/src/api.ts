// Thin client for the Python API. The session cookie travels automatically (same origin).

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body.detail ?? res.statusText);
  }
  return res.json() as Promise<T>;
}

export const post = <T,>(path: string, body: unknown) =>
  api<T>(path, { method: "POST", body: JSON.stringify(body) });

export const put = <T,>(path: string, body: unknown) =>
  api<T>(path, { method: "PUT", body: JSON.stringify(body) });

export type Me = { authenticated: boolean; login_enabled: boolean };
export type Profile = {
  account_type: "PEA" | "CTO";
  initial_amount_eur: number;
  monthly_amount_eur: number;
  core_share: number;
  satellite_share: number;
  horizon_years: number;
  updated_at?: string;
  core_isin: string;
  satellites_count: number;
  max_position_share: number;
  min_order_eur: number;
};
export type LlmStatus = Record<string, { provider: string; model: string }[]>;
export type LlmTest = { provider: string; model: string; answer: string };

export type InstrumentSummary = {
  isin: string;
  symbol: string;
  name: string;
  kind: "stock" | "etf";
  currency: string | null;
  exchange: string | null;
  country: string | null;
  sector: string | null;
  industry: string | null;
  pea_eligible: boolean | null;
  pea_reason: string | null;
  last_close: number | null;
  last_day: string | null;
  change_1y: number | null;
  prices_updated_at: string | null;
  fundamentals_updated_at: string | null;
};

export type FundamentalCell = {
  value: number;
  source: "esef" | "yahoo";
  url: string | null;
  currency: string | null;
  other_value: number | null;
  gap: number | null;
} | null;

export type InstrumentDetail = InstrumentSummary & {
  lei: string | null;
  years: string[];
  fundamentals: Record<string, FundamentalCell[]>;
  reports: { period_end: string; url: string }[];
};

export type PricePoint = { day: string; close: number; adj_close: number };
export type SeedState = { running: boolean; done: number; total: number; current: string | null; errors: string[] };

export type MetricResult = {
  key: string;
  label: string;
  fmt: "pct" | "x" | "num";
  help: string;
  good: number;
  bad: number;
  value: number | null;
  score: number | null;
  detail: string | null;
};
export type Pillar = { label: string; question: string; weight: number; score: number | null; metrics: MetricResult[] };
export type AnalysisData = {
  isin: string;
  kind: "stock" | "etf";
  score: number | null;
  verdict: string;
  pillars?: Record<string, Pillar>;
  strengths?: string[];
  weaknesses?: string[];
  warnings: string[];
  risk: Record<string, number>;
  info: Record<string, number | null>;
  info_labels: Record<string, [string, string]>;
  valuation?: { market_cap?: number; report_currency?: string; pe_history?: [number, number][] };
  yearly?: { years: string[]; rows: Record<string, ({ value: number; source: string } | null)[]> };
  sector_medians: Record<string, number>;
  computed_at: string;
};
export type RankingRow = {
  isin: string;
  name: string;
  sector: string | null;
  pea_eligible: boolean | null;
  score: number | null;
  verdict: string;
  pillars: Record<string, number | null>;
  metrics: Record<string, number | null>;
  return_1y: number | null;
};
export type Ranking = { pillars: Record<string, string>; rows: RankingRow[] };

export type PositionLine = {
  isin: string;
  name: string;
  kind: string | null;
  sector: string | null;
  role: "core" | "satellite";
  quantity: number;
  average_cost: number | null;
  cost: number;
  price: number | null;
  value: number | null;
  gain: number | null;
  gain_pct: number | null;
  weight: number | null;
};
export type TransactionRow = { id: number; day: string; isin: string; side: "buy" | "sell"; quantity: number; price_eur: number; fees_eur: number; note: string | null };
export type PortfolioData = {
  total_value: number;
  contributions: number;
  gain: number;
  core_weight: number | null;
  core_target: number;
  sectors: Record<string, number>;
  positions: PositionLine[];
  transactions: TransactionRow[];
  warnings: string[];
  rules: { core_isin: string; satellites_count: number; max_position_share: number; min_order_eur: number };
};
export type PlanOrder = { isin: string; name: string; amount: number; role: "core" | "satellite"; reason?: string };
export type PlanData = {
  monthly_amount: number;
  orders: PlanOrder[];
  targets: { isin: string; name: string; sector: string | null; score: number | null; pinned: boolean; held: boolean; reason: string }[];
  first_payment: PlanOrder[] | null;
};
export type SimStats = {
  final_value: number;
  invested: number;
  gain: number;
  money_weighted_return: number | null;
  time_weighted_return: number | null;
  volatility: number | null;
  max_drawdown: number | null;
  worst_12_months: number | null;
};
export type Projection = { invested: number; p10: number; p50: number; p90: number; loss_probability: number } | null;
export type SimulationData = {
  years: number;
  satellites: { isin: string; name: string }[];
  chart: { days: string[]; strategy: number[]; core_only: number[]; invested: number[] };
  strategy: SimStats;
  core_only: SimStats;
  projection: { horizon_years: number; long_run_rate: number; strategy: Projection; core_only: Projection; strategy_normalized: Projection; core_only_normalized: Projection };
  warnings: string[];
};

export type NewsRow = {
  id: number;
  isin: string | null;
  company: string | null;
  title: string;
  url: string;
  source: string | null;
  published_at: string;
  category: string | null;
  category_label: string;
  sentiment: number | null;
  importance: number | null;
  summary: string | null;
  triaged_by: string | null;
};
export type AlertRow = {
  id: number;
  isin: string;
  company: string;
  kind: "news" | "price";
  severity: number;
  title: string;
  detail: string | null;
  url: string | null;
  created_at: string;
  read: boolean;
};
export type DigestPoint = { text: string; sources: number[] };
export type DigestData = {
  created_at: string;
  points: DigestPoint[];
  watch: DigestPoint[];
  sources: { n: number; title: string; url: string; source: string | null; date: string }[];
  model: string;
};
