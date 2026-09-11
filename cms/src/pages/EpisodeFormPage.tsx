import { useEffect, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";

import { isApiError, useArtwork } from "../api/artwork";
import { useCreateEpisode, useDeleteEpisode, useEpisode, useUpdateEpisode } from "../api/episodes";
import type { PublishStatus } from "../api/types";
import { ArtworkUploadSlot } from "../components/ArtworkUploadSlot";
import { ErrorState, LoadingState } from "../components/States";
import { useToast } from "../components/Toast";

const LANGUAGES = ["en", "hi"];

export function EpisodeFormPage() {
  const { id } = useParams();
  const isNew = id === "new";
  const episodeId = isNew ? undefined : Number(id);
  const [searchParams] = useSearchParams();
  const seasonIdFromQuery = searchParams.get("seasonId");
  const navigate = useNavigate();
  const { showToast } = useToast();

  const { data: episode, isLoading, isError, error, refetch } = useEpisode(episodeId);
  const artwork = useArtwork("episode", episodeId);
  const createEpisode = useCreateEpisode();
  // See ShowFormPage for why this hook is always called unconditionally.
  const updateEpisode = useUpdateEpisode(episodeId ?? -1);
  const deleteEpisode = useDeleteEpisode();

  const [episodeNumber, setEpisodeNumber] = useState("");
  const [title, setTitle] = useState("");
  const [synopsis, setSynopsis] = useState("");
  const [durationSeconds, setDurationSeconds] = useState("");
  const [language, setLanguage] = useState("en");
  const [contentGroup, setContentGroup] = useState("");
  const [status, setStatus] = useState<PublishStatus>("draft");

  useEffect(() => {
    if (episode) {
      setEpisodeNumber(String(episode.episode_number));
      setTitle(episode.title);
      setSynopsis(episode.synopsis ?? "");
      setDurationSeconds(episode.duration_seconds ? String(episode.duration_seconds) : "");
      setLanguage(episode.language);
      setContentGroup(episode.content_group ?? "");
      setStatus(episode.status);
    }
  }, [episode]);

  if (!isNew && isLoading) return <LoadingState label="Loading episode…" />;
  if (!isNew && isError) {
    return (
      <ErrorState message={isApiError(error) ? error.message : "Failed to load episode."} onRetry={() => refetch()} />
    );
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const body = {
      title,
      synopsis: synopsis || null,
      duration_seconds: durationSeconds ? Number(durationSeconds) : null,
      language,
      content_group: contentGroup || null,
      status,
    };

    if (isNew) {
      if (!seasonIdFromQuery) return;
      createEpisode.mutate(
        { ...body, season_id: Number(seasonIdFromQuery), episode_number: Number(episodeNumber) },
        {
          onSuccess: (created) => {
            showToast("success", "Episode created.");
            navigate(`/episodes/${created.id}`, { replace: true });
          },
        },
      );
    } else {
      updateEpisode.mutate(body, {
        onSuccess: () => showToast("success", "Episode saved."),
      });
    }
  }

  function handleDelete() {
    if (!episodeId) return;
    if (!window.confirm(`Delete episode "${title}"? This cannot be undone.`)) return;

    deleteEpisode.mutate(episodeId, {
      onSuccess: () => {
        showToast("success", "Episode deleted.");
        navigate("/episodes", { replace: true });
      },
      onError: (err) => {
        showToast("error", isApiError(err) ? err.message : "Delete failed.");
      },
    });
  }

  const mutation = isNew ? createEpisode : updateEpisode;

  return (
    <div>
      <div className="page-header">
        <h1>{isNew ? "New episode" : title}</h1>
        <Link to="/episodes">&larr; Back to episodes</Link>
      </div>

      <form onSubmit={handleSubmit} className="entity-form">
        {isNew && (
          <>
            <label htmlFor="episode-number">Episode number</label>
            <input
              id="episode-number"
              type="number"
              required
              value={episodeNumber}
              onChange={(e) => setEpisodeNumber(e.target.value)}
            />
          </>
        )}

        <label htmlFor="title">Title</label>
        <input id="title" required value={title} onChange={(e) => setTitle(e.target.value)} />

        <label htmlFor="synopsis">Synopsis</label>
        <textarea id="synopsis" value={synopsis} onChange={(e) => setSynopsis(e.target.value)} />

        <label htmlFor="duration">Duration (seconds)</label>
        <input
          id="duration"
          type="number"
          value={durationSeconds}
          onChange={(e) => setDurationSeconds(e.target.value)}
        />

        <label htmlFor="language">Language</label>
        <select id="language" value={language} onChange={(e) => setLanguage(e.target.value)}>
          {LANGUAGES.map((l) => (
            <option key={l} value={l}>
              {l}
            </option>
          ))}
        </select>

        <label htmlFor="content-group">
          Content group <span className="hint">(shared across language variants of the same episode)</span>
        </label>
        <input id="content-group" value={contentGroup} onChange={(e) => setContentGroup(e.target.value)} />

        <label htmlFor="status">Status</label>
        <select id="status" value={status} onChange={(e) => setStatus(e.target.value as PublishStatus)}>
          <option value="draft">Draft</option>
          <option value="published">Published</option>
        </select>

        <button type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? "Saving…" : "Save"}
        </button>
        {!isNew && (
          <button type="button" className="button-danger" disabled={deleteEpisode.isPending} onClick={handleDelete}>
            {deleteEpisode.isPending ? "Deleting…" : "Delete episode"}
          </button>
        )}

        {mutation.isError && (
          <p className="field-error" role="alert">
            {isApiError(mutation.error) ? mutation.error.message : "Save failed."}
          </p>
        )}
        {deleteEpisode.isError && (
          <p className="field-error" role="alert">
            {isApiError(deleteEpisode.error) ? deleteEpisode.error.message : "Delete failed."}
          </p>
        )}
      </form>

      {!isNew && episode && (
        <section className="artwork-section">
          <h2>Artwork</h2>
          <div className="artwork-slots">
            <ArtworkUploadSlot
              kind="thumbnail"
              ownerType="episode"
              ownerId={episode.id}
              label="Thumbnail"
              requiredDims="640×360 (16:9)"
              maxKb={200}
              currentUrl={artwork.data?.find((item) => item.kind === "thumbnail")?.url ?? null}
            />
          </div>
        </section>
      )}
    </div>
  );
}
