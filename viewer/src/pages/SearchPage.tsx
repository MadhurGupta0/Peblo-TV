import { useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { useCatalog, useCatalogSearch } from "../api/catalog";
import { AsyncImage } from "../components/AsyncImage";
import { EmptyState, ErrorState, LoadingState } from "../components/States";

const LANGUAGE_OPTIONS = ["", "en", "hi"];

export function SearchPage() {
  const [params, setParams] = useSearchParams();
  const q = params.get("q") ?? "";
  const category = params.get("category") ?? "";
  const language = params.get("language") ?? "";

  const catalog = useCatalog();
  const results = useCatalogSearch({ q: q || undefined, category: category || undefined, language: language || undefined });

  const categories = useMemo(() => {
    const all = new Set<string>();
    for (const section of catalog.data?.sections ?? []) {
      for (const show of section.shows) {
        for (const item of show.categories) {
          all.add(item);
        }
      }
    }
    return ["", ...Array.from(all).sort((left, right) => left.localeCompare(right))];
  }, [catalog.data]);

  function updateParam(key: string, value: string) {
    const next = new URLSearchParams(params);
    if (value) {
      next.set(key, value);
    } else {
      next.delete(key);
    }
    setParams(next, { replace: true });
  }

  if (catalog.isLoading || results.isLoading) {
    return <LoadingState label="Searching catalog" />;
  }

  if (catalog.isError || results.isError) {
    return <ErrorState message="Search is unavailable right now." onRetry={() => void results.refetch()} />;
  }

  const shows = results.data?.shows ?? [];
  const emptyReason = [language === "hi" ? "Hindi" : language === "en" ? "English" : "all languages", category || null]
    .filter(Boolean)
    .join(" + ");

  return (
    <div className="search-page">
      <div className="search-header">
        <div>
          <p className="eyebrow">Search catalog</p>
          <h1>Find a show fast</h1>
        </div>
        <p>{shows.length} results</p>
      </div>

      <form className="search-filters" onSubmit={(event) => event.preventDefault()}>
        <label>
          Search
          <input value={q} onChange={(event) => updateParam("q", event.target.value)} placeholder="Search title, episode, or category" />
        </label>
        <label>
          Category
          <select value={category} onChange={(event) => updateParam("category", event.target.value)}>
            {categories.map((option) => (
              <option key={option || "all"} value={option}>
                {option || "All categories"}
              </option>
            ))}
          </select>
        </label>
        <label>
          Language
          <select value={language} onChange={(event) => updateParam("language", event.target.value)}>
            {LANGUAGE_OPTIONS.map((option) => (
              <option key={option || "all"} value={option}>
                {option || "All languages"}
              </option>
            ))}
          </select>
        </label>
      </form>

      {shows.length === 0 ? (
        <EmptyState
          title="No shows match those filters"
          detail={`No shows match ${emptyReason || "the current filters"} — try clearing a filter.`}
        />
      ) : (
        <div className="search-grid">
          {shows.map((show) => (
            <Link key={`${show.section ?? "unknown"}-${show.id}`} to={`/shows/${show.slug}`} className="search-card">
              <AsyncImage src={show.artwork.poster} alt={`${show.title} poster`} ratio="poster" />
              <div className="search-card-copy">
                <strong>{show.title}</strong>
                <span>{show.section}</span>
                <span>{show.categories.join(" · ")}</span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}