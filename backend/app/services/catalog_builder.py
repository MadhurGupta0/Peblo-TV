from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.reference_data import SECTION_ORDER
from app.models.artwork import Artwork
from app.models.enums import ArtworkOwnerType, PublishStatus
from app.models.episode import Episode
from app.models.season import Season
from app.models.show import Show
from app.services.publish_rules import EPISODE_REQUIRED_ARTWORK
from app.storage import Storage

TRAILER_SEASON_NUMBER = 0


def _artwork_urls(storage: Storage, artworks: list[Artwork]) -> dict[str, str]:
    return {a.kind.value: storage.url_for(a.storage_key) for a in artworks}


def _episode_entry(variants: list[Episode], artwork_by_episode: dict[int, list[Artwork]], storage: Storage) -> dict:
    # Canonical variant = alphabetically-first language code. Deterministic and total:
    # (content_group, language) is unique, so no two variants in a group can tie on language.
    canonical = min(variants, key=lambda e: e.language)
    languages = sorted(v.language for v in variants)
    return {
        "id": canonical.id,
        "episode_number": canonical.episode_number,
        "title": canonical.title,
        "synopsis": canonical.synopsis,
        "duration_seconds": canonical.duration_seconds,
        "languages": languages,
        "content_group": canonical.content_group,
        "artwork": _artwork_urls(storage, artwork_by_episode.get(canonical.id, [])),
    }


def _group_episodes_by_content(episodes: list[Episode]) -> list[list[Episode]]:
    groups: dict[str, list[Episode]] = {}
    order: list[str] = []
    for ep in episodes:
        key = ep.content_group or f"__solo_{ep.id}"
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(ep)
    return [groups[k] for k in order]


def build_catalogue_content(db: Session, storage: Storage) -> tuple[dict, dict]:
    """Returns (content, counts). `content` is everything that goes into the checksum —
    no generated_at/run_id, so re-publishing unchanged data yields an identical checksum
    (the idempotency guarantee)."""
    shows = (
        db.execute(
            select(Show)
            .where(Show.status == PublishStatus.published)
            .options(selectinload(Show.seasons).selectinload(Season.episodes))
            .order_by(Show.title, Show.id)
        )
        .scalars()
        .all()
    )

    show_ids = [s.id for s in shows]
    episode_ids = [e.id for s in shows for season in s.seasons for e in season.episodes]

    show_artwork: dict[int, list[Artwork]] = {}
    episode_artwork: dict[int, list[Artwork]] = {}
    if show_ids:
        for a in db.execute(select(Artwork).where(Artwork.owner_type == ArtworkOwnerType.show, Artwork.owner_id.in_(show_ids))).scalars():
            show_artwork.setdefault(a.owner_id, []).append(a)
    if episode_ids:
        for a in db.execute(
            select(Artwork).where(Artwork.owner_type == ArtworkOwnerType.episode, Artwork.owner_id.in_(episode_ids))
        ).scalars():
            episode_artwork.setdefault(a.owner_id, []).append(a)

    sections: dict[str, list[dict]] = {}
    show_count = episode_count = 0

    for show in shows:
        # Re-check the business rules here, not just at write time (see WORKFLOW.md §2.5):
        # the seeder inserts rows directly and bypasses API validation, so a row can be
        # status=published in the DB while failing a rule the API would have blocked. Such
        # rows are demoted for this run (excluded, not errored) and surfaced instead via
        # GET /admin/validation-report.
        if show.section is None:
            continue  # can't be placed under any section; also can't have passed assert_show_publishable

        published_by_season: dict[int, list[Episode]] = {}
        for season in show.seasons:
            published = [
                e
                for e in season.episodes
                if e.status == PublishStatus.published
                and e.duration_seconds
                and any(a.kind == EPISODE_REQUIRED_ARTWORK for a in episode_artwork.get(e.id, []))
            ]
            if published:
                published_by_season[season.season_number] = published

        if not published_by_season:
            continue  # drop shows with zero publishable episodes, even if status=published

        trailers_raw = published_by_season.pop(TRAILER_SEASON_NUMBER, [])
        trailers = [
            _episode_entry(group, episode_artwork, storage)
            for group in _group_episodes_by_content(sorted(trailers_raw, key=lambda e: e.episode_number))
        ]

        seasons_out = []
        for season_number in sorted(published_by_season):
            episodes_sorted = sorted(published_by_season[season_number], key=lambda e: e.episode_number)
            entries = [_episode_entry(group, episode_artwork, storage) for group in _group_episodes_by_content(episodes_sorted)]
            seasons_out.append({"season_number": season_number, "episodes": entries})
            episode_count += len(entries)
        episode_count += len(trailers)

        if not seasons_out and not trailers:
            continue

        show_count += 1
        show_entry = {
            "id": show.id,
            "slug": show.slug,
            "title": show.title,
            "synopsis": show.synopsis,
            "categories": show.categories,
            "artwork": _artwork_urls(storage, show_artwork.get(show.id, [])),
            "seasons": seasons_out,
            "trailers": trailers,
        }
        sections.setdefault(show.section, []).append(show_entry)

    ordered_sections = [
        {"section": section, "shows": sections[section]} for section in SECTION_ORDER if section in sections
    ]
    # Any section not in SECTION_ORDER (shouldn't happen given the enum, but don't silently
    # drop data if it does) is appended after the canonical ones, alphabetically.
    leftover = sorted(set(sections) - set(SECTION_ORDER))
    ordered_sections += [{"section": section, "shows": sections[section]} for section in leftover]

    content = {"sections": ordered_sections}
    counts = {"shows": show_count, "episodes": episode_count, "sections": len(ordered_sections)}
    return content, counts
