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
