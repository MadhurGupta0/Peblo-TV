import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "./client";
import type { Episode, Page, PublishStatus } from "./types";

export interface EpisodeFilters {
  section?: string;
  status?: PublishStatus;
  language?: string;
  q?: string;
  show_id?: number;
  season_id?: number;
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

export function useEpisodes(filters: EpisodeFilters) {
  return useQuery({
    queryKey: ["episodes", filters],
    queryFn: () => apiFetch<Page<Episode>>(`/episodes${toQuery(filters as unknown as Record<string, string | number | undefined>)}`),
  });
}

export function useEpisode(episodeId: number | undefined) {
  return useQuery({
    queryKey: ["episodes", episodeId],
    queryFn: () => apiFetch<Episode>(`/episodes/${episodeId}`),
    enabled: episodeId !== undefined,
  });
}

export function useCreateEpisode() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: Partial<Episode> & { season_id: number }) =>
      apiFetch<Episode>("/episodes", { method: "POST", body: JSON.stringify(body) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["episodes"] });
      queryClient.invalidateQueries({ queryKey: ["validation-report"] });
    },
  });
}

export function useUpdateEpisode(episodeId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: Partial<Episode>) =>
      apiFetch<Episode>(`/episodes/${episodeId}`, { method: "PATCH", body: JSON.stringify(body) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["episodes"] });
      queryClient.invalidateQueries({ queryKey: ["validation-report"] });
    },
  });
}

export function useDeleteEpisode() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (episodeId: number) => apiFetch<void>(`/episodes/${episodeId}`, { method: "DELETE" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["episodes"] }),
  });
}
