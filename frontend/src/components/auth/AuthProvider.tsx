import {
  createContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react";
import { useQueryClient } from "@tanstack/react-query";
import * as authApi from "../../api/auth";
import type { AccountUsage, AuthAccount, AuthUser } from "../../types";

export type SignupOutcome =
  | { ok: true; needsVerification: true; userId: number; email: string }
  | { ok: false; error?: string };

export type LoginOutcome =
  | { ok: true }
  | { ok: false; error?: string; userId?: number; email?: string };

export interface AuthContextValue {
  isAuthenticated: boolean;
  isLoading: boolean;
  isAdmin: boolean;
  user: AuthUser | null;
  account: AuthAccount | null;
  usage: AccountUsage | null;
  login: (email: string, password: string) => Promise<LoginOutcome>;
  signup: (email: string, password: string, name?: string, locale?: string) => Promise<SignupOutcome>;
  verifyEmail: (userId: number, code: string) => Promise<boolean>;
  applyAuthPayload: (payload: authApi.AuthPayload) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue>({
  isAuthenticated: false,
  isLoading: true,
  isAdmin: false,
  user: null,
  account: null,
  usage: null,
  login: async () => ({ ok: false }),
  signup: async () => ({ ok: false }),
  verifyEmail: async () => false,
  applyAuthPayload: async () => {},
  logout: async () => {},
  refresh: async () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [isLoading, setIsLoading] = useState(true);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [account, setAccount] = useState<AuthAccount | null>(null);
  const [usage, setUsage] = useState<AccountUsage | null>(null);

  const applyPayload = useCallback((payload: authApi.AuthPayload | { authenticated: false }) => {
    if (!payload.authenticated) {
      setUser(null);
      setAccount(null);
      setUsage(null);
      return;
    }
    setUser(payload.user);
    setAccount(payload.account);
    setUsage(payload.usage);
  }, []);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    try {
      applyPayload(await authApi.getMe());
    } finally {
      setIsLoading(false);
    }
  }, [applyPayload]);

  // Listen for 401 events from apiFetch
  useEffect(() => {
    const handler = () => {
      setUser(null);
      setAccount(null);
      setUsage(null);
      queryClient.cancelQueries();
    };
    window.addEventListener("opencmo:unauthorized", handler);
    return () => window.removeEventListener("opencmo:unauthorized", handler);
  }, [queryClient]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const applyAuthPayload = useCallback(
    async (payload: authApi.AuthPayload) => {
      applyPayload(payload);
      await queryClient.invalidateQueries();
    },
    [applyPayload, queryClient],
  );

  const login = useCallback(
    async (email: string, password: string): Promise<LoginOutcome> => {
      try {
        const payload = await authApi.login({ email, password });
        applyPayload(payload);
        await queryClient.invalidateQueries();
        return { ok: true };
      } catch (err) {
        const apiErr = err as {
          errorCode?: string;
          message?: string;
          payload?: { user_id?: number; email?: string; error?: string };
        };
        const code = apiErr?.errorCode ?? apiErr?.payload?.error ?? apiErr?.message ?? "";
        if (code === "email_not_verified") {
          return {
            ok: false,
            error: "email_not_verified",
            userId: apiErr.payload?.user_id,
            email: apiErr.payload?.email,
          };
        }
        return { ok: false, error: code || apiErr?.message };
      }
    },
    [applyPayload, queryClient],
  );

  const signup = useCallback(
    async (email: string, password: string, name?: string, locale?: string): Promise<SignupOutcome> => {
      try {
        const payload = await authApi.signup({ email, password, name, locale });
        if (payload.needs_verification) {
          return {
            ok: true,
            needsVerification: true,
            userId: payload.user_id,
            email: payload.email,
          };
        }
        // Legacy fallback: server may still return an AuthPayload shape.
        return { ok: false, error: "unexpected_response" };
      } catch (err) {
        const apiErr = err as { message?: string };
        return { ok: false, error: apiErr?.message };
      }
    },
    [],
  );

  const verifyEmail = useCallback(
    async (userId: number, code: string) => {
      try {
        const payload = await authApi.verifyEmail({ user_id: userId, code });
        applyPayload(payload);
        await queryClient.invalidateQueries();
        return true;
      } catch {
        return false;
      }
    },
    [applyPayload, queryClient],
  );

  const logout = useCallback(async () => {
    await authApi.logout().catch(() => undefined);
    localStorage.removeItem("opencmo_token");
    setUser(null);
    setAccount(null);
    setUsage(null);
    queryClient.clear();
  }, [queryClient]);

  const isAuthenticated = !!user;
  const isAdmin = user?.role === "admin";

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated,
        isLoading,
        isAdmin,
        user,
        account,
        usage,
        login,
        signup,
        verifyEmail,
        applyAuthPayload,
        logout,
        refresh,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
