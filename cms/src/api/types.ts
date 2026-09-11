export type UserRole = "editor" | "admin";
export type PublishStatus = "draft" | "published";

export interface User {
  id: number;
  email: string;
  role: UserRole;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface Show {
  id: number;
  slug: string;
  title: string;
  synopsis: string | null;
  section: string | null;
  categories: string[];
  status: PublishStatus;
}

export interface Season {
  id: number;
  show_id: number;
  season_number: number;
  title: string | null;
}

export interface Episode {
  id: number;
  season_id: number;
  episode_number: number;
  title: string;
  synopsis: string | null;
  duration_seconds: number | null;
  language: string;
  content_group: string | null;
  status: PublishStatus;
}

export interface Artwork {
  id: number;
  owner_type: "show" | "episode";
  owner_id: number;
  kind: "poster" | "banner" | "thumbnail";
  url: string;
  width: number;
  height: number;
  bytes: number;
  content_type: string;
  checksum: string;
}

export interface ValidationIssue {
  field: string;
  code: string;
  message: string;
}

export interface ValidationReportEpisode {
  episode_id: number;
  season_number: number;
  episode_number: number;
  title: string;
  issues: ValidationIssue[];
}

export interface ValidationReportShow {
  show_id: number;
  title: string;
  slug: string;
  issues: ValidationIssue[];
  episodes: ValidationReportEpisode[];
}

export interface ValidationReport {
  shows: ValidationReportShow[];
  total_blocking_issues: number;
}

export interface PublishRun {
  run_id: number;
  actor_email: string | null;
  status: "running" | "success" | "failed";
  counts: Record<string, number>;
  catalogue_key: string | null;
  checksum: string | null;
  error: string | null;
  started_at: string;
  finished_at: string | null;
  duration_seconds: number | null;
}
