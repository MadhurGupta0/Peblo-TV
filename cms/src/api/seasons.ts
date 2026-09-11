import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "./client";
import type { Season } from "./types";

export function useSeasons(showId: number | undefined) {
  return useQuery({
    queryKey: ["seasons", showId],
    queryFn: () => apiFetch<Season[]>(`/shows/${showId}/seasons`),
    enabled: showId !== undefined,
  });
}

export function useCreateSeason(showId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: { season_number: number; title?: string }) =>
      apiFetch<Season>(`/shows/${showId}/seasons`, { method: "POST", body: JSON.stringify(body) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["seasons", showId] }),
  });
}
