import { Link } from "react-router-dom";

import type { CatalogShow } from "../api/types";
import { AsyncImage } from "./AsyncImage";

export function SectionRow({ title, shows }: { title: string; shows: CatalogShow[] }) {
  return (
    <section className="section-row">
      <div className="section-row-header">
        <h2>{title}</h2>
        <span>{shows.length} shows</span>
      </div>
      <div className="poster-row">
        {shows.map((show) => (
          <Link key={show.id} to={`/shows/${show.slug}`} className="poster-card">
            <AsyncImage src={show.artwork.poster} alt={`${show.title} poster`} ratio="poster" />
            <div className="poster-card-copy">
              <strong>{show.title}</strong>
              <span>{show.categories.join(" · ")}</span>
            </div>
          </Link>
        ))}
      </div>
    </section>
  );
}