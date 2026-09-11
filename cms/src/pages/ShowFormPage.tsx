import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { isApiError, useArtwork } from "../api/artwork";
import { useEpisodes } from "../api/episodes";
import { useCreateSeason, useSeasons } from "../api/seasons";
import { useCreateShow, useDeleteShow, useShow, useUpdateShow } from "../api/shows";
import type { PublishStatus } from "../api/types";
import { ArtworkUploadSlot } from "../components/ArtworkUploadSlot";
import { ErrorState, LoadingState } from "../components/States";
import { useToast } from "../components/Toast";

const SECTIONS = ["featured", "series", "minisodes", "songs"];

export function ShowFormPage() {
  const { id } = useParams();
  const isNew = id === "new";
  const showId = isNew ? undefined : Number(id);
  const navigate = useNavigate();
  const { showToast } = useToast();

  const { data: show, isLoading, isError, error, refetch } = useShow(showId);
  const artwork = useArtwork("show", showId);
  const createShow = useCreateShow();
  // Always call the hook (Rules of Hooks) — navigating from /shows/new to /shows/:id
  // after creation reuses this component instance without remounting, so a conditional
  // hook call here would change the hook count between renders and crash React.
  const updateShow = useUpdateShow(showId ?? -1);
  const deleteShow = useDeleteShow();

  const [title, setTitle] = useState("");
  const [slug, setSlug] = useState("");
  const [synopsis, setSynopsis] = useState("");
  const [section, setSection] = useState("");
  const [categories, setCategories] = useState("");
  const [status, setStatus] = useState<PublishStatus>("draft");

  useEffect(() => {
    if (show) {
      setTitle(show.title);
      setSlug(show.slug);
      setSynopsis(show.synopsis ?? "");
      setSection(show.section ?? "");
      setCategories(show.categories.join(", "));
      setStatus(show.status);
    }
  }, [show]);

  if (!isNew && isLoading) return <LoadingState label="Loading show…" />;
  if (!isNew && isError) {
    return (
      <ErrorState message={isApiError(error) ? error.message : "Failed to load show."} onRetry={() => refetch()} />
    );
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const body = {
      title,
      synopsis: synopsis || null,
      section: section || null,
      categories: categories
        .split(",")
        .map((c) => c.trim())
        .filter(Boolean),
      status,
    };

    if (isNew) {
      createShow.mutate(
        { ...body, slug },
        {
          onSuccess: (created) => {
            showToast("success", "Show created.");
            navigate(`/shows/${created.id}`, { replace: true });
          },
        },
      );
    } else {
      updateShow.mutate(body, {
        onSuccess: () => showToast("success", "Show saved."),
      });
    }
  }

  function handleDelete() {
    if (!showId) return;
    if (!window.confirm(`Delete "${title}"? This removes the show and its nested records.`)) return;

    deleteShow.mutate(showId, {
      onSuccess: () => {
        showToast("success", "Show deleted.");
        navigate("/shows", { replace: true });
      },
      onError: (err) => {
        showToast("error", isApiError(err) ? err.message : "Delete failed.");
      },
    });
  }

  const mutation = isNew ? createShow : updateShow;

  return (
    <div>
      <div className="page-header">
        <h1>{isNew ? "New show" : title}</h1>
        <Link to="/shows">&larr; Back to shows</Link>
      </div>

      <form onSubmit={handleSubmit} className="entity-form">
        <label htmlFor="title">Title</label>
        <input id="title" required value={title} onChange={(e) => setTitle(e.target.value)} />

        {isNew && (
          <>
            <label htmlFor="slug">Slug</label>
            <input id="slug" required value={slug} onChange={(e) => setSlug(e.target.value)} />
          </>
        )}

        <label htmlFor="synopsis">Synopsis</label>
        <textarea id="synopsis" value={synopsis} onChange={(e) => setSynopsis(e.target.value)} />

        <label htmlFor="section">Section</label>
        <select id="section" value={section} onChange={(e) => setSection(e.target.value)}>
          <option value="">None</option>
          {SECTIONS.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>

        <label htmlFor="categories">Categories (comma-separated)</label>
        <input id="categories" value={categories} onChange={(e) => setCategories(e.target.value)} />

        <label htmlFor="status">Status</label>
        <select id="status" value={status} onChange={(e) => setStatus(e.target.value as PublishStatus)}>
          <option value="draft">Draft</option>
          <option value="published">Published</option>
        </select>

        <button type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? "Saving…" : "Save"}
        </button>
        {!isNew && (
          <button type="button" className="button-danger" disabled={deleteShow.isPending} onClick={handleDelete}>
            {deleteShow.isPending ? "Deleting…" : "Delete show"}
          </button>
        )}

        {mutation.isError && (
          <p className="field-error" role="alert">
            {isApiError(mutation.error) ? mutation.error.message : "Save failed."}
          </p>
        )}
        {deleteShow.isError && (
          <p className="field-error" role="alert">
            {isApiError(deleteShow.error) ? deleteShow.error.message : "Delete failed."}
          </p>
        )}
      </form>

      {!isNew && show && (
        <>
          <section className="artwork-section">
            <h2>Artwork</h2>
            <div className="artwork-slots">
              <ArtworkUploadSlot
                kind="poster"
                ownerType="show"
                ownerId={show.id}
                label="Poster"
                requiredDims="600×900 (2:3)"
                maxKb={200}
                currentUrl={artwork.data?.find((item) => item.kind === "poster")?.url ?? null}
              />
              <ArtworkUploadSlot
                kind="banner"
                ownerType="show"
                ownerId={show.id}
                label="Banner"
                requiredDims="1280×720 (16:9)"
                maxKb={200}
                currentUrl={artwork.data?.find((item) => item.kind === "banner")?.url ?? null}
              />
            </div>
          </section>

          <SeasonsSection showId={show.id} />
        </>
      )}
    </div>
  );
}

function SeasonsSection({ showId }: { showId: number }) {
  const { data: seasons, isLoading, isError, error, refetch } = useSeasons(showId);
  const createSeason = useCreateSeason(showId);
  const [newSeasonNumber, setNewSeasonNumber] = useState("");
  const { showToast } = useToast();

  function handleAddSeason(e: React.FormEvent) {
    e.preventDefault();
    const num = Number(newSeasonNumber);
    if (Number.isNaN(num)) return;
    createSeason.mutate(
      { season_number: num },
      {
        onSuccess: () => {
          showToast("success", `Season ${num} added.`);
          setNewSeasonNumber("");
        },
      },
    );
  }

  return (
    <section className="seasons-section">
      <h2>Seasons</h2>
      {isLoading && <LoadingState label="Loading seasons…" />}
      {isError && (
        <ErrorState message={isApiError(error) ? error.message : "Failed to load seasons."} onRetry={() => refetch()} />
      )}
      {seasons && seasons.length === 0 && <p>No seasons yet.</p>}
      {seasons?.map((season) => (
        <SeasonBlock key={season.id} showId={showId} seasonId={season.id} seasonNumber={season.season_number} />
      ))}

      <form onSubmit={handleAddSeason} className="inline-form">
        <label htmlFor="new-season-number">
          Add season (use 0 for trailers)
        </label>
        <input
          id="new-season-number"
          type="number"
          required
          value={newSeasonNumber}
          onChange={(e) => setNewSeasonNumber(e.target.value)}
        />
        <button type="submit" disabled={createSeason.isPending}>
          Add season
        </button>
      </form>
    </section>
  );
}

function SeasonBlock({ showId, seasonId, seasonNumber }: { showId: number; seasonId: number; seasonNumber: number }) {
  const { data } = useEpisodes({ season_id: seasonId, page: 1, page_size: 100 });

  return (
    <div className="season-block">
      <h3>{seasonNumber === 0 ? "Trailers" : `Season ${seasonNumber}`}</h3>
      <ul>
        {data?.items.map((ep) => (
          <li key={ep.id}>
            <Link to={`/episodes/${ep.id}`}>
              Ep {ep.episode_number}: {ep.title}
            </Link>{" "}
            <span className={`status-badge status-${ep.status}`}>{ep.status}</span>
          </li>
        ))}
        {data?.items.length === 0 && <li className="muted">No episodes yet.</li>}
      </ul>
      <Link to={`/episodes/new?showId=${showId}&seasonId=${seasonId}`}>+ Add episode</Link>
    </div>
  );
}
