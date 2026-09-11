import { Link, useSearchParams } from "react-router-dom";

import { useShows } from "../api/shows";
import { isApiError } from "../api/artwork";
import { Pagination } from "../components/Pagination";
import { EmptyState, ErrorState, LoadingState } from "../components/States";

const SECTIONS = ["featured", "series", "minisodes", "songs"];
const LANGUAGES = ["en", "hi"];
const PAGE_SIZE = 20;

export function ShowsListPage() {
  const [params, setParams] = useSearchParams();
  const section = params.get("section") ?? "";
  const status = params.get("status") ?? "";
  const language = params.get("language") ?? "";
  const q = params.get("q") ?? "";
  const page = Number(params.get("page") ?? "1");

  const { data, isLoading, isError, error, refetch } = useShows({
    section: section || undefined,
    status: (status || undefined) as "draft" | "published" | undefined,
    language: language || undefined,
    q: q || undefined,
    page,
    page_size: PAGE_SIZE,
  });

  function updateParam(key: string, value: string, resetPage = true) {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    if (resetPage) next.set("page", "1");
    setParams(next);
  }

  return (
    <div>
      <div className="page-header">
        <h1>Shows</h1>
        <Link to="/shows/new" className="button-primary">
          + New show
        </Link>
      </div>

      <div className="filter-bar">
        <label>
          Search
          <input
            type="search"
            value={q}
            placeholder="Title or synopsis…"
            onChange={(e) => updateParam("q", e.target.value)}
          />
        </label>
        <label>
          Section
          <select value={section} onChange={(e) => updateParam("section", e.target.value)}>
            <option value="">All</option>
            {SECTIONS.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <label>
          Status
          <select value={status} onChange={(e) => updateParam("status", e.target.value)}>
            <option value="">All</option>
            <option value="draft">Draft</option>
            <option value="published">Published</option>
          </select>
        </label>
        <label>
          Language
          <select value={language} onChange={(e) => updateParam("language", e.target.value)}>
            <option value="">All</option>
            {LANGUAGES.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
      </div>

      {isLoading && <LoadingState label="Loading shows…" />}
      {isError && (
        <ErrorState message={isApiError(error) ? error.message : "Failed to load shows."} onRetry={() => refetch()} />
      )}
      {data && data.items.length === 0 && <EmptyState message="No shows match these filters." />}

      {data && data.items.length > 0 && (
        <>
          <table className="data-table">
            <thead>
              <tr>
                <th>Title</th>
                <th>Section</th>
                <th>Status</th>
                <th>Categories</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((show) => (
                <tr key={show.id}>
                  <td>
                    <Link to={`/shows/${show.id}`}>{show.title}</Link>
                  </td>
                  <td>{show.section ?? <em>none</em>}</td>
                  <td>
                    <span className={`status-badge status-${show.status}`}>{show.status}</span>
                  </td>
                  <td>{show.categories.join(", ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <Pagination
            page={data.page}
            pageSize={data.page_size}
            total={data.total}
            onPageChange={(p) => updateParam("page", String(p), false)}
          />
        </>
      )}
    </div>
  );
}
