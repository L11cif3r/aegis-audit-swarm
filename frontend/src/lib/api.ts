// Shared API client for the Talamanda Trust Layer backend.
// Base URL is configurable via VITE_API_URL (see frontend/.env.example).

import {
  clearSession,
  getRefreshToken,
  getToken,
  notifyUnauthorized,
  setSession,
  type AuthUser,
} from "./session";

export const API_BASE: string =
  (import.meta as any).env?.VITE_API_URL?.replace(/\/$/, "") ||
  "http://127.0.0.1:8000";

const API_KEY: string | undefined = (import.meta as any).env?.VITE_API_KEY;

// Endpoints that must never trigger the refresh-and-retry flow (a 401 here is a
// genuine credential/refresh failure, not an expired access token).
const NO_REFRESH = ["/auth/login", "/auth/signup", "/auth/refresh"];

function headers(): HeadersInit {
  const h: Record<string, string> = { "Content-Type": "application/json" };
  const token = getToken();
  if (token) h["Authorization"] = `Bearer ${token}`;
  else if (API_KEY) h["X-API-Key"] = API_KEY;
  return h;
}

// Single-flight refresh: many concurrent 401s share one refresh round-trip.
let refreshPromise: Promise<boolean> | null = null;

async function doRefresh(): Promise<boolean> {
  const refresh_token = getRefreshToken();
  if (!refresh_token) return false;
  try {
    const res = await fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token }),
    });
    if (!res.ok) return false;
    const data = (await res.json()) as AuthSession;
    // Persist the new access token + rotated refresh token + user.
    setSession(data.token, data.user, data.refresh_token);
    return true;
  } catch {
    return false;
  }
}

function refreshOnce(): Promise<boolean> {
  if (!refreshPromise) {
    refreshPromise = doRefresh().finally(() => {
      refreshPromise = null;
    });
  }
  return refreshPromise;
}

async function request<T>(
  method: "GET" | "POST",
  path: string,
  body?: unknown,
  retried = false,
): Promise<T> {
  const init: RequestInit = { method, headers: headers() };
  if (method === "POST") init.body = JSON.stringify(body ?? {});
  const res = await fetch(`${API_BASE}${path}`, init);

  if (res.status === 401) {
    if (!retried && !NO_REFRESH.includes(path)) {
      const ok = await refreshOnce();
      if (ok) return request<T>(method, path, body, true);
    }
    clearSession();
    notifyUnauthorized();
    throw new Error(`${method} ${path} -> 401`);
  }

  if (!res.ok) {
    let detail = "";
    try {
      detail = (await res.json())?.detail ?? "";
    } catch {
      /* non-json error body */
    }
    throw new Error(detail || `${method} ${path} -> ${res.status}`);
  }
  return res.json();
}

export async function apiGet<T = any>(path: string): Promise<T> {
  return request<T>("GET", path);
}

export async function apiPost<T = any>(path: string, body: unknown): Promise<T> {
  return request<T>("POST", path, body);
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

export type AuthSession = { token: string; refresh_token: string; user: AuthUser };

// Convenience typed endpoints.
export const api = {
  logs: (limit = 100) => apiGet(`/audit/logs?limit=${limit}`),
  stats: () => apiGet(`/audit/stats`),
  threats: () => apiGet(`/audit/threats`),
  costSummary: () => apiGet(`/cost/summary`),
  analystSummary: (limit = 60) =>
    apiGet<{ summary: string; model: string | null; generated: boolean }>(
      `/analyst/summary?limit=${limit}`,
    ),
  analystExplain: (id: string) =>
    apiPost<{ explanation: string; model: string }>(`/analyst/explain`, { id }),
  assistantChat: (messages: { role: string; content: string }[]) =>
    apiPost<{ reply: string; model: string }>(`/assistant/chat`, { messages }),
  getBudget: () => apiGet(`/cost/budget`),
  setBudget: (body: { daily_limit_usd: number | null; monthly_limit_usd: number | null }) =>
    apiPost(`/cost/budget`, body),
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
  auth: {
    signup: (body: { email: string; password: string; display_name?: string }) =>
      apiPost<AuthSession>(`/auth/signup`, body),
    login: (body: { email: string; password: string }) =>
      apiPost<AuthSession>(`/auth/login`, body),
    me: () => apiGet<AuthUser>(`/auth/me`),
    logout: (refresh_token?: string | null) =>
      apiPost(`/auth/logout`, { refresh_token: refresh_token ?? null }),
    rotateApiKey: () => apiPost<{ ingress_api_key: string }>(`/auth/api-key/rotate`, {}),
    changePassword: (body: { current_password: string; new_password: string }) =>
      apiPost<{ ok: boolean }>(`/auth/change-password`, body),
    forgotPassword: (email: string) =>
      apiPost<{ ok: boolean; message: string }>(`/auth/forgot-password`, { email }),
    resetPassword: (body: { token: string; new_password: string }) =>
      apiPost<{ ok: boolean }>(`/auth/reset-password`, body),
    verifyEmail: (token: string) =>
      apiPost<{ ok: boolean }>(`/auth/verify-email`, { token }),
    resendVerification: () =>
      apiPost<{ ok: boolean; message?: string }>(`/auth/resend-verification`, {}),
  },
};
