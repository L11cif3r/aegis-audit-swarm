// Lightweight session/token store (no React, no api imports) so the API client
// and the auth context can both depend on it without a cycle.

export type AuthUser = {
  id: string;
  email: string | null;
  tenant: string;
  display_name?: string | null;
  role?: string;
  ingress_api_key?: string | null;
  created_at?: string | null;
};

const TOKEN_KEY = "aatl_token";
const REFRESH_KEY = "aatl_refresh";
const USER_KEY = "aatl_user";

export const UNAUTHORIZED_EVENT = "aatl:unauthorized";

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function getRefreshToken(): string | null {
  try {
    return localStorage.getItem(REFRESH_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string): void {
  try {
    localStorage.setItem(TOKEN_KEY, token);
  } catch {
    /* storage unavailable */
  }
}

export function getUser(): AuthUser | null {
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? (JSON.parse(raw) as AuthUser) : null;
  } catch {
    return null;
  }
}

export function setSession(token: string, user: AuthUser, refreshToken?: string): void {
  try {
    localStorage.setItem(TOKEN_KEY, token);
    if (refreshToken) localStorage.setItem(REFRESH_KEY, refreshToken);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  } catch {
    /* storage unavailable */
  }
}

export function setUser(user: AuthUser): void {
  try {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  } catch {
    /* storage unavailable */
  }
}

export function clearSession(): void {
  try {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(USER_KEY);
  } catch {
    /* storage unavailable */
  }
}

export function isAuthed(): boolean {
  return !!getToken();
}

export function notifyUnauthorized(): void {
  try {
    window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
  } catch {
    /* non-browser */
  }
}
