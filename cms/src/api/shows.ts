import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "./client";
import type { Page, Show, PublishStatus } from "./types";

export interface ShowFilters {
  section?: string;
  status?: PublishStatus;
  language?: string;
  q?: string;
  page: number;
  page_size: number;
}

function toQuery(filters: Record<string, string | number | undefined>): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== "") params.set(key, String(value));
  }
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

export function useShows(filters: ShowFilters) {
  return useQuery({
    queryKey: ["shows", filters],
    queryFn: () => apiFetch<Page<Show>>(`/shows${toQuery(filters as unknown as Record<string, string | number | undefined>)}`),
  });
}

export function useShow(showId: number | undefined) {
  return useQuery({
    queryKey: ["shows", showId],
    queryFn: () => apiFetch<Show>(`/shows/${showId}`),
    enabled: showId !== undefined,
  });
}

export function useCreateShow() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: Partial<Show>) => apiFetch<Show>("/shows", { method: "POST", body: JSON.stringify(body) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["shows"] }),
  });
}

export function useUpdateShow(showId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: Partial<Show>) =>
      apiFetch<Show>(`/shows/${showId}`, { method: "PATCH", body: JSON.stringify(body) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["shows"] });
      queryClient.invalidateQueries({ queryKey: ["validation-report"] });
    },
  });
}

export function useDeleteShow() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (showId: number) => apiFetch<void>(`/shows/${showId}`, { method: "DELETE" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["shows"] }),
  });
}
