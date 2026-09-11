import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "./client";
import type { Page, PublishRun, ValidationReport } from "./types";

export function useValidationReport() {
  return useQuery({
    queryKey: ["validation-report"],
    queryFn: () => apiFetch<ValidationReport>("/admin/validation-report"),
  });
}

export function usePublishRuns(page: number) {
  return useQuery({
    queryKey: ["publish-runs", page],
    queryFn: () => apiFetch<Page<PublishRun>>(`/admin/publish-runs?page=${page}&page_size=10`),
  });
}

export function usePublish() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => apiFetch<PublishRun>("/admin/catalog/publish", { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["publish-runs"] });
      queryClient.invalidateQueries({ queryKey: ["validation-report"] });
    },
  });
}
