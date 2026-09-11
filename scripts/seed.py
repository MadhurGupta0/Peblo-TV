"""Idempotent seeder: loads _given/seed_shows.json into Postgres.

Run from the repo root with the backend's venv active and DATABASE_URL set
(the api container runs this automatically after migrations):

    PYTHONPATH=backend python scripts/seed.py

Decisions (see docs/DATA_FINDINGS.md for the full recon):
- A row whose (content_group, language) collides with an already-imported row is
  rejected, logged, and skipped rather than aborting the whole run — that collision
  is deliberate seed data exercising the UNIQUE constraint.
- Show.status/section/categories aren't in the seed schema directly; they're derived
  from the show's episode rows (section/categories are just carried on every row for
  that show; status = published if any episode is published, else draft).
- Re-running is safe: shows/seasons/episodes are upserted by their natural keys
  (slug; (show, season_number); (season, episode_number, language)).
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from PIL import Image  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.exc import IntegrityError  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models.artwork import Artwork  # noqa: E402
from app.models.enums import ArtworkKind, ArtworkOwnerType, PublishStatus, UserRole  # noqa: E402
from app.models.episode import Episode  # noqa: E402
from app.models.season import Season  # noqa: E402
from app.models.show import Show  # noqa: E402
from app.models.user import User  # noqa: E402
from app.storage import get_storage  # noqa: E402

GIVEN = ROOT / "_given"
ASSETS = GIVEN / "assets"

ARTWORK_FILES = {
    ArtworkKind.poster.value: "poster_good.jpg",
    ArtworkKind.banner.value: "banner_good.jpg",
    ArtworkKind.thumbnail.value: "thumb_good.jpg",
}


def load_rows() -> list[dict]:
    return json.loads((GIVEN / "seed_shows.json").read_text(encoding="utf-8"))


def seed_users(db) -> None:
    settings = get_settings()
    for email, password, role in (
        (settings.seed_editor_email, settings.seed_editor_password, UserRole.editor),
        (settings.seed_admin_email, settings.seed_admin_password, UserRole.admin),
    ):
        existing = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if existing:
            continue
        db.add(User(email=email, hashed_password=hash_password(password), role=role))
    db.commit()
    print(f"users: ensured {settings.seed_editor_email} (editor), {settings.seed_admin_email} (admin)")


def upsert_artwork(db, *, owner_type: ArtworkOwnerType, owner_id: int, kind: ArtworkKind, uploaded_by: int) -> None:
    file_name = ARTWORK_FILES[kind.value]
    source = ASSETS / file_name
    data = source.read_bytes()
    with Image.open(source) as image:
        width, height = image.size

    content_type = "image/jpeg" if source.suffix.lower() == ".jpg" else "image/png"
    storage_key = f"artwork/{owner_type.value}/{owner_id}/{kind.value}{source.suffix.lower()}"
    checksum = hashlib.sha256(data).hexdigest()

    storage = get_storage()
    storage.put(storage_key, data, content_type)

    artwork = db.execute(
        select(Artwork).where(
            Artwork.owner_type == owner_type,
            Artwork.owner_id == owner_id,
            Artwork.kind == kind,
        )
    ).scalar_one_or_none()
    if artwork is None:
        artwork = Artwork(owner_type=owner_type, owner_id=owner_id, kind=kind)
        db.add(artwork)

    artwork.storage_key = storage_key
    artwork.width = width
    artwork.height = height
    artwork.bytes = len(data)
    artwork.content_type = content_type
    artwork.checksum = checksum
    artwork.uploaded_by = uploaded_by


def seed_artwork(db, rows: list[dict]) -> None:
    admin_user = db.execute(select(User).where(User.role == UserRole.admin)).scalar_one()

    show_by_slug = {show.slug: show for show in db.execute(select(Show)).scalars().all()}
    episode_by_key = {
        (show.slug, season.season_number, episode.episode_number, episode.language): episode
        for show in db.execute(select(Show)).scalars().all()
        for season in show.seasons
        for episode in season.episodes
    }

    seeded_show_art = set()
    seeded_episode_art = set()

    for row in rows:
        show = show_by_slug.get(row["slug"])
        if show is None:
            continue

        for kind_name in row.get("artwork_available", []):
            kind = ArtworkKind(kind_name)
            if kind in (ArtworkKind.poster, ArtworkKind.banner):
                show_key = (show.id, kind)
                if show_key not in seeded_show_art:
                    upsert_artwork(
                        db,
                        owner_type=ArtworkOwnerType.show,
                        owner_id=show.id,
                        kind=kind,
                        uploaded_by=admin_user.id,
                    )
                    seeded_show_art.add(show_key)
                continue

            episode = episode_by_key.get((row["slug"], row["season_number"], row["episode_number"], row["language"]))
            if episode is None:
                continue

            episode_key = (episode.id, kind)
            if episode_key in seeded_episode_art:
                continue
            upsert_artwork(
                db,
                owner_type=ArtworkOwnerType.episode,
                owner_id=episode.id,
                kind=kind,
                uploaded_by=admin_user.id,
            )
            seeded_episode_art.add(episode_key)

    db.commit()
    print(f"artwork: shows {len(seeded_show_art)}  episodes {len(seeded_episode_art)}")


def seed_shows(db, rows: list[dict]) -> None:
    by_slug: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_slug[row["slug"]].append(row)

    rejected: list[tuple[str, str]] = []
    show_count = season_count = episode_count = 0
    # natural key -> episode_id of the row that first claimed it. A second, *different*
    # episode_id targeting the same (show, season, episode_number, language) is a genuine
    # conflict in the source data (see docs/DATA_FINDINGS.md #1) — it must be rejected and
    # logged, not silently overwrite the row already seeded from the first episode_id.
    claimed_by: dict[tuple[str, int, int, str], str] = {}

    for slug, show_rows in by_slug.items():
        first = show_rows[0]
        categories = sorted({c for r in show_rows for c in r["categories"]})
        any_published = any(r["status"] == "published" for r in show_rows)

        show = db.execute(select(Show).where(Show.slug == slug)).scalar_one_or_none()
        if show is None:
            show = Show(slug=slug)
            db.add(show)
        show.title = first["show_title"]
        show.synopsis = first["synopsis"]
        show.section = first["section"]
        show.categories = categories
        show.status = PublishStatus.published if any_published else PublishStatus.draft
        db.flush()
        show_count += 1

        seasons_by_number: dict[int, Season] = {}
        for row in show_rows:
            season_number = row["season_number"]
            season = seasons_by_number.get(season_number)
            if season is None:
                season = db.execute(
                    select(Season).where(Season.show_id == show.id, Season.season_number == season_number)
                ).scalar_one_or_none()
                if season is None:
                    season = Season(show_id=show.id, season_number=season_number)
                    db.add(season)
                    db.flush()
                    season_count += 1
                seasons_by_number[season_number] = season

            natural_key = (slug, season_number, row["episode_number"], row["language"])
            claimant = claimed_by.get(natural_key)
            if claimant is not None and claimant != row["episode_id"]:
                rejected.append(
                    (row["episode_id"], f"conflicts with already-imported {claimant} on the same episode slot")
                )
                continue
            claimed_by[natural_key] = row["episode_id"]

            episode = db.execute(
                select(Episode).where(
                    Episode.season_id == season.id,
                    Episode.episode_number == row["episode_number"],
                    Episode.language == row["language"],
                )
            ).scalar_one_or_none()
            if episode is None:
                episode = Episode(season_id=season.id, episode_number=row["episode_number"], language=row["language"])
                db.add(episode)

            episode.title = row["episode_title"]
            episode.synopsis = row["synopsis"]
            episode.duration_seconds = row["duration_seconds"]
            episode.content_group = row["content_group"]
            episode.status = PublishStatus(row["status"])

            try:
                db.flush()
                episode_count += 1
            except IntegrityError:
                db.rollback()
                rejected.append((row["episode_id"], "duplicate (content_group, language)"))

    db.commit()
    print(f"shows: {show_count}  seasons: {season_count}  episodes: {episode_count}")
    if rejected:
        print("rejected rows (surfaced in validation report, not silently dropped):")
        for episode_id, reason in rejected:
            print(f"  {episode_id}: {reason}")


def main() -> None:
    rows = load_rows()
    with SessionLocal() as db:
        seed_users(db)
        seed_shows(db, rows)
        seed_artwork(db, rows)


if __name__ == "__main__":
    main()
