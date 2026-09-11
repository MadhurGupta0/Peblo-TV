export type CatalogEpisode = {
  id: number;
  episode_number: number;
  title: string;
  synopsis: string;
  duration_seconds: number;
  languages: string[];
  content_group: string | null;
  artwork: Record<string, string>;
};

export type CatalogSeason = {
  season_number: number;
  episodes: CatalogEpisode[];
};

export type CatalogShow = {
  id: number;
  slug: string;
  title: string;
  synopsis: string;
  categories: string[];
  artwork: Record<string, string>;
  seasons: CatalogSeason[];
  trailers: CatalogEpisode[];
  section?: string;
};

export type CatalogSection = {
  section: string;
  shows: CatalogShow[];
};

export type CatalogResponse = {
  schema_version: number;
  run_id: number | null;
  generated_at: string | null;
  checksum: string | null;
  sections: CatalogSection[];
};

export type CatalogSearchResponse = {
  shows: CatalogShow[];
};