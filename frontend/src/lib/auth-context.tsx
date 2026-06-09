"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { apiRequest, clearTokens, setTokens } from "./api";
import type { AuthResponse, User, WorkspaceMembership } from "./types";

interface AuthContextValue {
  user: User | null;
  memberships: WorkspaceMembership[];
  currentWorkspaceId: string | null;
  setCurrentWorkspaceId: (id: string) => void;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, full_name: string) => Promise<void>;
  logout: () => void;
  loading: boolean;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const WS_KEY = "miq.current_workspace_id";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [memberships, setMemberships] = useState<WorkspaceMembership[]>([]);
  const [currentWorkspaceId, _setCurrentWorkspaceId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const setCurrentWorkspaceId = useCallback((id: string) => {
    _setCurrentWorkspaceId(id);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(WS_KEY, id);
    }
  }, []);

  const applyAuth = useCallback(
    (resp: AuthResponse) => {
      setTokens(resp.tokens.access_token, resp.tokens.refresh_token);
      setUser(resp.user);
      setMemberships(resp.memberships);
      if (resp.memberships.length > 0) {
        const stored =
          typeof window !== "undefined" ? window.localStorage.getItem(WS_KEY) : null;
        const wsId =
          stored && resp.memberships.some((m) => m.workspace_id === stored)
            ? stored
            : resp.memberships[0].workspace_id;
        setCurrentWorkspaceId(wsId);
      }
    },
    [setCurrentWorkspaceId],
  );

  const refresh = useCallback(async () => {
    try {
      const me = await apiRequest<{ user: User; memberships: WorkspaceMembership[] }>(
        "/users/me",
      );
      setUser(me.user);
      setMemberships(me.memberships);
      if (me.memberships.length > 0 && !currentWorkspaceId) {
        const stored =
          typeof window !== "undefined" ? window.localStorage.getItem(WS_KEY) : null;
        const wsId =
          stored && me.memberships.some((m) => m.workspace_id === stored)
            ? stored
            : me.memberships[0].workspace_id;
        setCurrentWorkspaceId(wsId);
      }
    } catch {
      setUser(null);
      setMemberships([]);
      clearTokens();
    } finally {
      setLoading(false);
    }
  }, [currentWorkspaceId, setCurrentWorkspaceId]);

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      const resp = await apiRequest<AuthResponse>("/auth/login", {
        method: "POST",
        body: { email, password },
      });
      applyAuth(resp);
    },
    [applyAuth],
  );

  const signup = useCallback(
    async (email: string, password: string, full_name: string) => {
      const resp = await apiRequest<AuthResponse>("/auth/signup", {
        method: "POST",
        body: { email, password, full_name },
      });
      applyAuth(resp);
    },
    [applyAuth],
  );

  const logout = useCallback(() => {
    clearTokens();
    setUser(null);
    setMemberships([]);
    _setCurrentWorkspaceId(null);
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(WS_KEY);
    }
    router.push("/login");
  }, [router]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      memberships,
      currentWorkspaceId,
      setCurrentWorkspaceId,
      login,
      signup,
      logout,
      loading,
      refresh,
    }),
    [user, memberships, currentWorkspaceId, setCurrentWorkspaceId, login, signup, logout, loading, refresh],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
