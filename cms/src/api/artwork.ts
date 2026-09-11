import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError, apiFetch } from "./client";
import type { Artwork } from "./types";

export interface UploadArtworkVars {
  file: File;
  kind: "poster" | "banner" | "thumbnail";
  ownerType: "show" | "episode";
  ownerId: number;
}

export function useArtwork(ownerType: "show" | "episode", ownerId: number | undefined) {
  return useQuery({
    queryKey: ["artwork", ownerType, ownerId],
    queryFn: () => apiFetch<Artwork[]>(`/admin/artwork?owner_type=${ownerType}&owner_id=${ownerId}`),
    enabled: ownerId !== undefined,
  });
}

export function useUploadArtwork() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ file, kind, ownerType, ownerId }: UploadArtworkVars) => {
      const form = new FormData();
      form.set("file", file);
      form.set("kind", kind);
      form.set("owner_type", ownerType);
      form.set("owner_id", String(ownerId));
      return apiFetch<Artwork>("/admin/artwork", { method: "POST", body: form });
    },
    onSuccess: (_data, vars) => {
      queryClient.invalidateQueries({ queryKey: ["artwork", vars.ownerType, vars.ownerId] });
      queryClient.invalidateQueries({ queryKey: ["validation-report"] });
    },
  });
}

export function isApiError(err: unknown): err is ApiError {
  return err instanceof ApiError;
}
