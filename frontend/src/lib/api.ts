// Shared API client for the Talamanda Trust Layer backend.
// Base URL is configurable via VITE_API_URL (see frontend/.env.example).

export const API_BASE: string =
  (import.meta as any).env?.VITE_API_URL?.replace(/\/$/, "") ||
  "http://127.0.0.1:8000";

const API_KEY: string | undefined = (import.meta as any).env?.VITE_API_KEY;

function headers(): HeadersInit {
  const h: Record<string, string> = { "Content-Type": "application/json" };
  if (API_KEY) h["X-API-Key"] = API_KEY;
  return h;
}

export async function apiGet<T = any>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { headers: headers() });
  if (!res.ok) throw new Error(`GET ${path} -> ${res.status}`);
  return res.json();
}

export async function apiPost<T = any>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`POST ${path} -> ${res.status}`);
  return res.json();
}

export type ModelPrice = {
  input_price_per_m: number;
  output_price_per_m: number;
};

export type ProviderConfig = {
  provider: string;
  display_name: string;
  kind: "builtin" | "custom";
  default_model: string;
  base_url: string;
  chat_endpoint?: string;
  input_price: number;
  output_price: number;
  input_price_per_m: number;
  output_price_per_m: number;
  enabled: boolean;
  api_key_set: boolean;
  api_key_masked: string | null;
  api_key_source: string;
  models: string[];
  model_prices?: Record<string, ModelPrice>;
};

export type CatalogModel = {
  id: string;
  input_price_per_m: number;
  output_price_per_m: number;
};

export type CatalogEntry = {
  id: string;
  label: string;
  default_model: string;
  models: CatalogModel[];
};

export type ProviderCatalog = Record<string, CatalogEntry>;

export type ProviderTestResult = {
  ok: boolean;
  provider: string;
  model?: string;
  latency_ms?: number;
  message?: string;
  error?: string;
  response?: string;
};

export type ProxyRequestBody = {
  agent: string;
  prompt: string;
  model?: string;
  task?: string;
  max_tokens?: number;
  metadata?: Record<string, unknown>;
};

// Convenience typed endpoints.
export const api = {
  logs: (limit = 100) => apiGet(`/audit/logs?limit=${limit}`),
  stats: () => apiGet(`/audit/stats`),
  threats: () => apiGet(`/audit/threats`),
  controls: (framework?: string) =>
    apiGet(`/library/controls${framework ? `?framework=${framework}` : ""}`),
  coverage: () => apiGet(`/library/coverage`),
  adversaryFindings: (limit = 100) => apiGet(`/adversary/findings?limit=${limit}`),
  adversaryCoverage: () => apiGet(`/adversary/coverage`),
  trustScore: () => apiGet(`/notary/trust-score`),
  ledger: (limit = 200) => apiGet(`/notary/ledger?limit=${limit}`),
  verifyLedger: () => apiGet(`/notary/verify`),
  certificate: (tenant = "default") => apiGet(`/notary/certificate?tenant=${tenant}`),
  reviewPending: () => apiGet(`/review/pending`),
  resolveReview: (id: string, decision: "approved" | "rejected") =>
    apiPost(`/review/${id}`, { decision }),
  providers: () => apiGet<ProviderConfig[]>(`/gateway/providers`),
  catalog: () => apiGet<ProviderCatalog>(`/gateway/catalog`),
  updateProvider: (id: string, body: Record<string, unknown>) =>
    apiPost<ProviderConfig>(`/gateway/providers/${id}`, body),
  testProvider: (id: string, model?: string) =>
    apiPost<ProviderTestResult>(`/gateway/providers/${id}/test`, model ? { model } : {}),
  proxyRequest: (body: ProxyRequestBody) => apiPost(`/agent/request`, body),
};
