import { useCatalog } from "../api/catalog";
import { AsyncImage } from "../components/AsyncImage";
import { EmptyState, ErrorState, LoadingState } from "../components/States";
import { SectionRow } from "../components/SectionRow";

export function HomePage() {
  const catalog = useCatalog();

  if (catalog.isLoading) {
    return <LoadingState label="Loading catalog" />;
  }

  if (catalog.isError) {
    return <ErrorState message="The catalogue could not be loaded." onRetry={() => void catalog.refetch()} />;
  }

  const sections = catalog.data?.sections ?? [];
  const featured = sections.flatMap((section) => section.shows)[0];

  if (!featured) {
    return <EmptyState title="Nothing published yet" detail="Publish a catalogue from the CMS to populate the viewer." />;
  }

  return (
    <div className="home-page">
      <section className="hero-card">
        <AsyncImage src={featured.artwork.banner} alt={`${featured.title} banner`} ratio="banner" className="hero-media" />
        <div className="hero-copy">
          <p className="eyebrow">Featured now</p>
          <h1>{featured.title}</h1>
          <p>{featured.synopsis}</p>
          <div className="hero-meta">
            <span>{featured.categories.join(" · ")}</span>
            <span>{featured.seasons.length} seasons</span>
            <span>{featured.trailers.length} trailers</span>
          </div>
        </div>
      </section>

      {sections.map((section) => (
        <SectionRow key={section.section} title={section.section} shows={section.shows} />
      ))}
    </div>
  );
}