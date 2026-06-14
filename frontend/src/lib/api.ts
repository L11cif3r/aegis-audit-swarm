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
};
