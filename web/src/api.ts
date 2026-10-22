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

export type Me = { authenticated: boolean; login_enabled: boolean };
export type Profile = {
  account_type: string;
  initial_amount_eur: number;
  monthly_amount_eur: number;
  core_share: number;
  satellite_share: number;
};
export type LlmStatus = Record<string, { provider: string; model: string }[]>;
export type LlmTest = { provider: string; model: string; answer: string };
