// React auth context: wraps the session store + auth API endpoints and exposes
// login/signup/logout to the app. Listens for 401s to auto-logout.
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { api } from "./api";
import {
  clearSession,
  getRefreshToken,
  getUser,
  isAuthed,
  setSession,
  setUser as persistUser,
  UNAUTHORIZED_EVENT,
  type AuthUser,
} from "./session";

interface AuthContextValue {
  user: AuthUser | null;
  authed: boolean;
  ready: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, displayName?: string) => Promise<void>;
  logout: () => void;
  refresh: () => Promise<void>;
  rotateApiKey: () => Promise<string | null>;
  changePassword: (currentPassword: string, newPassword: string) => Promise<void>;
  resendVerification: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUserState] = useState<AuthUser | null>(() => getUser());
  const [authed, setAuthed] = useState<boolean>(() => isAuthed());
  const [ready, setReady] = useState(false);

  const applySession = useCallback((token: string, u: AuthUser, refreshToken?: string) => {
    setSession(token, u, refreshToken);
    setUserState(u);
    setAuthed(true);
  }, []);

  const logout = useCallback(() => {
    api.auth.logout(getRefreshToken()).catch(() => {});
    clearSession();
    setUserState(null);
    setAuthed(false);
  }, []);

  const refresh = useCallback(async () => {
    if (!isAuthed()) {
      setReady(true);
      return;
    }
    try {
      const me = await api.auth.me();
      persistUser(me);
      setUserState(me);
      setAuthed(true);
    } catch {
      clearSession();
      setUserState(null);
      setAuthed(false);
    } finally {
      setReady(true);
    }
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      const { token, refresh_token, user: u } = await api.auth.login({ email, password });
      applySession(token, u, refresh_token);
    },
    [applySession],
  );

  const signup = useCallback(
    async (email: string, password: string, displayName?: string) => {
      const { token, refresh_token, user: u } = await api.auth.signup({
        email,
        password,
        display_name: displayName,
      });
      applySession(token, u, refresh_token);
    },
    [applySession],
  );

  const rotateApiKey = useCallback(async () => {
    const { ingress_api_key } = await api.auth.rotateApiKey();
    if (user) {
      const next = { ...user, ingress_api_key };
      persistUser(next);
      setUserState(next);
    }
    return ingress_api_key;
  }, [user]);

  const changePassword = useCallback(
    async (currentPassword: string, newPassword: string) => {
      await api.auth.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      });
      // All sessions were invalidated server-side; force re-login.
      clearSession();
      setUserState(null);
      setAuthed(false);
    },
    [],
  );

  const resendVerification = useCallback(async () => {
    await api.auth.resendVerification();
  }, []);

  // Validate any persisted token on mount.
  useEffect(() => {
    void refresh();
  }, [refresh]);

  // Global 401 handler -> drop session.
  useEffect(() => {
    const onUnauthorized = () => {
      setUserState(null);
      setAuthed(false);
    };
    window.addEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user, authed, ready, login, signup, logout, refresh, rotateApiKey,
      changePassword, resendVerification,
    }),
    [user, authed, ready, login, signup, logout, refresh, rotateApiKey,
     changePassword, resendVerification],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
