import { useMemo } from "react";
import { useParams } from "react-router-dom";

import { useCatalog } from "../api/catalog";
import type { CatalogEpisode } from "../api/types";
import { AsyncImage } from "../components/AsyncImage";
import { EmptyState, ErrorState, LoadingState } from "../components/States";

function formatDuration(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const remainder = seconds % 60;
  return `${minutes}m ${String(remainder).padStart(2, "0")}s`;
}

function EpisodeCard({ episode }: { episode: CatalogEpisode }) {
  return (
    <article className="episode-card">
      <AsyncImage src={episode.artwork.thumbnail} alt={`${episode.title} thumbnail`} ratio="thumb" />
      <div className="episode-copy">
        <div className="episode-meta">
          <strong>
            Episode {episode.episode_number}: {episode.title}
          </strong>
          <span>{formatDuration(episode.duration_seconds)}</span>
        </div>
        <p>{episode.synopsis}</p>
        <div className="language-chips">
          {episode.languages.map((language) => (
            <span key={language} className="language-chip">
              {language.toUpperCase()}
            </span>
          ))}
        </div>
      </div>
    </article>
  );
}

export function ShowDetailPage() {
  const { slug } = useParams();
  const catalog = useCatalog();

  const show = useMemo(() => {
    for (const section of catalog.data?.sections ?? []) {
      const match = section.shows.find((item) => item.slug === slug);
      if (match) {
        return { ...match, section: section.section };
      }
    }
    return null;
  }, [catalog.data, slug]);

  if (catalog.isLoading) {
    return <LoadingState label="Loading show" />;
  }

  if (catalog.isError) {
    return <ErrorState message="The show could not be loaded." onRetry={() => void catalog.refetch()} />;
  }

  if (!show) {
    return <EmptyState title="Show not found" detail="This title is not in the published catalog right now." />;
  }

  return (
    <div className="show-page">
      <section className="show-hero">
        <AsyncImage src={show.artwork.banner} alt={`${show.title} banner`} ratio="banner" className="show-hero-media" />
        <div className="show-hero-copy">
          <p className="eyebrow">{show.section}</p>
          <h1>{show.title}</h1>
          <p>{show.synopsis}</p>
          <div className="hero-meta">
            <span>{show.categories.join(" · ")}</span>
            <span>{show.seasons.length} seasons</span>
            <span>{show.trailers.length} trailers</span>
          </div>
        </div>
      </section>

      {show.trailers.length > 0 ? (
        <section className="detail-section">
          <h2>Trailers</h2>
          <div className="episode-stack">
            {show.trailers.map((episode) => (
              <EpisodeCard key={episode.id} episode={episode} />
            ))}
          </div>
        </section>
      ) : null}

      {show.seasons.map((season) => (
        <section key={season.season_number} className="detail-section">
          <h2>Season {season.season_number}</h2>
          <div className="episode-stack">
            {season.episodes.map((episode) => (
              <EpisodeCard key={episode.id} episode={episode} />
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}