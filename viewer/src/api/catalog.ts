import { useQuery } from "@tanstack/react-query";

import { getJson } from "./client";
import type { CatalogResponse, CatalogSearchResponse } from "./types";

export type SearchFilters = {
  q?: string;
  category?: string;
  language?: string;
};

export function useCatalog() {
  return useQuery({
    queryKey: ["catalog"],
    queryFn: () => getJson<CatalogResponse>("/catalog"),
  });
}

export function useCatalogSearch(filters: SearchFilters) {
  const params = new URLSearchParams();
  if (filters.q) params.set("q", filters.q);
  if (filters.category) params.set("category", filters.category);
  if (filters.language) params.set("language", filters.language);
  const query = params.toString();

  return useQuery({
    queryKey: ["catalog-search", filters],
    queryFn: () => getJson<CatalogSearchResponse>(`/catalog/search${query ? `?${query}` : ""}`),
  });
}