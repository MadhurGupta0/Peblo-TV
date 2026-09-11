import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch, setToken } from "./client";
import type { User } from "./types";

export function useMe(enabled: boolean) {
  return useQuery({
    queryKey: ["me"],
    queryFn: () => apiFetch<User>("/auth/me"),
    enabled,
    retry: false,
  });
}

export function useLogin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (vars: { email: string; password: string }) => {
      const { access_token } = await apiFetch<{ access_token: string; token_type: string }>("/auth/login", {
        method: "POST",
        body: JSON.stringify(vars),
        skipAuth: true,
      });
      setToken(access_token);
      return access_token;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["me"] });
    },
  });
}

export function logout(queryClient: ReturnType<typeof useQueryClient>) {
  setToken(null);
  queryClient.clear();
}
