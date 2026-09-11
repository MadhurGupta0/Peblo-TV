import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { logout as doLogout, useMe } from "../api/auth";
import { getToken, subscribeToken } from "../api/client";
import type { User } from "../api/types";

interface AuthContextValue {
  user: User | undefined;
  isLoading: boolean;
  isAuthenticated: boolean;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  // Mirrors client.ts's token in React state — plain module state wouldn't re-render
  // anything when setToken() is called from a mutation's onSuccess outside the component tree.
  const [hasToken, setHasToken] = useState(() => getToken() !== null);
  useEffect(() => subscribeToken((token) => setHasToken(token !== null)), []);

  const { data: user, isLoading, isError } = useMe(hasToken);
  const queryClient = useQueryClient();

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isLoading: hasToken && isLoading,
      isAuthenticated: hasToken && !isError && user !== undefined,
      logout: () => doLogout(queryClient),
    }),
    [user, isLoading, isError, hasToken, queryClient],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
