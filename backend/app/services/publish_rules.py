from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppValidationError
from app.models.artwork import Artwork
from app.models.enums import ArtworkKind, ArtworkOwnerType
from app.models.episode import Episode
from app.models.show import Show

# An episode's own artwork is only ever its thumbnail (episode lists in the viewer use
# thumbnails; poster/banner are show-level, used for rows and the hero). So "an episode
# can't be published without artwork" means: does it have a thumbnail.
EPISODE_REQUIRED_ARTWORK = ArtworkKind.thumbnail


def _has_artwork(db: Session, owner_type: ArtworkOwnerType, owner_id: int, kind: ArtworkKind) -> bool:
    return (
        db.execute(
            select(Artwork.id).where(
                Artwork.owner_type == owner_type, Artwork.owner_id == owner_id, Artwork.kind == kind
            )
        ).scalar_one_or_none()
        is not None
    )


def assert_show_publishable(show: Show) -> None:
    if show.section is None:
        raise AppValidationError.single(
            "section", "missing_section", f'"{show.title}" can\'t be published without a section.'
        )


def assert_episode_publishable(db: Session, episode: Episode) -> None:
    errors = []
    if not episode.duration_seconds:
        errors.append(
            {"field": "duration_seconds", "code": "missing_duration", "message": "This episode needs a duration before it can be published."}
        )
    if not _has_artwork(db, ArtworkOwnerType.episode, episode.id, EPISODE_REQUIRED_ARTWORK):
        errors.append(
            {
                "field": "artwork",
                "code": "missing_artwork",
                "message": f"This episode has no {EPISODE_REQUIRED_ARTWORK.value} — upload one before publishing.",
            }
        )
    if errors:
        raise AppValidationError(errors)


def show_issues(show: Show) -> list[dict]:
    """Non-raising form for the validation report — same rule, reported instead of enforced."""
    try:
        assert_show_publishable(show)
        return []
    except AppValidationError as exc:
        return exc.errors


def episode_issues(db: Session, episode: Episode) -> list[dict]:
    try:
        assert_episode_publishable(db, episode)
        return []
    except AppValidationError as exc:
        return exc.errors
