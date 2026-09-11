from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.core.database import get_db
from app.core.errors import AppValidationError
from app.models.enums import PublishStatus, UserRole
from app.models.episode import Episode
from app.models.season import Season
from app.models.show import Show
from app.schemas.common import Page
from app.schemas.episode import EpisodeCreate, EpisodeOut, EpisodeUpdate
from app.services.publish_rules import assert_episode_publishable

router = APIRouter(prefix="/episodes", tags=["episodes"])

_editor_or_admin = require_role(UserRole.editor, UserRole.admin)


def _commit_or_conflict(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError:
        # Roll back here (not in the global handler) because this is the one place that
        # still holds the live session — a handler given only the Request can't reach it,
        # and a broken, un-rolled-back session would poison every later query on it.
        db.rollback()
        raise AppValidationError.single(
            "content_group", "conflict", "Another episode already uses this content_group and language combination.", status_code=status.HTTP_409_CONFLICT
        ) from None


@router.get("", response_model=Page[EpisodeOut])
def list_episodes(
    section: str | None = Query(default=None),
    status_: PublishStatus | None = Query(default=None, alias="status"),
    language: str | None = Query(default=None),
    q: str | None = Query(default=None),
    show_id: int | None = Query(default=None),
    season_id: int | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _user=Depends(_editor_or_admin),
) -> Page:
    stmt = select(Episode).join(Season, Episode.season_id == Season.id)
    if section is not None or show_id is not None:
        stmt = stmt.join(Show, Season.show_id == Show.id)
        if section is not None:
            stmt = stmt.where(Show.section == section)
        if show_id is not None:
            stmt = stmt.where(Show.id == show_id)
    if season_id is not None:
        stmt = stmt.where(Episode.season_id == season_id)
    if status_ is not None:
        stmt = stmt.where(Episode.status == status_)
    if language is not None:
        stmt = stmt.where(Episode.language == language)
    if q:
        stmt = stmt.where(Episode.title.ilike(f"%{q}%"))

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = (
        db.execute(stmt.order_by(Episode.season_id, Episode.episode_number).offset((page - 1) * page_size).limit(page_size))
        .scalars()
        .all()
    )
    return Page(items=[EpisodeOut.model_validate(r) for r in rows], total=total, page=page, page_size=page_size)


@router.get("/{episode_id}", response_model=EpisodeOut)
def get_episode(episode_id: int, db: Session = Depends(get_db), _user=Depends(_editor_or_admin)) -> Episode:
    episode = db.get(Episode, episode_id)
    if episode is None:
        raise AppValidationError.single("episode_id", "not_found", "Episode not found.", status_code=status.HTTP_404_NOT_FOUND)
    return episode


@router.post("", response_model=EpisodeOut, status_code=status.HTTP_201_CREATED)
def create_episode(body: EpisodeCreate, db: Session = Depends(get_db), _user=Depends(_editor_or_admin)) -> Episode:
    season = db.get(Season, body.season_id)
    if season is None:
        raise AppValidationError.single("season_id", "not_found", "Season not found.", status_code=status.HTTP_404_NOT_FOUND)

    episode = Episode(**body.model_dump())
    if episode.status == PublishStatus.published:
        db.add(episode)
        db.flush()  # need an id before checking for artwork rows against it
        assert_episode_publishable(db, episode)
    else:
        db.add(episode)

    _commit_or_conflict(db)
    db.refresh(episode)
    return episode


@router.patch("/{episode_id}", response_model=EpisodeOut)
def update_episode(episode_id: int, body: EpisodeUpdate, db: Session = Depends(get_db), _user=Depends(_editor_or_admin)) -> Episode:
    episode = db.get(Episode, episode_id)
    if episode is None:
        raise AppValidationError.single("episode_id", "not_found", "Episode not found.", status_code=status.HTTP_404_NOT_FOUND)

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(episode, field, value)

    if episode.status == PublishStatus.published:
        db.flush()
        assert_episode_publishable(db, episode)

    _commit_or_conflict(db)
    db.refresh(episode)
    return episode


@router.delete("/{episode_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_episode(episode_id: int, db: Session = Depends(get_db), _user=Depends(_editor_or_admin)) -> None:
    episode = db.get(Episode, episode_id)
    if episode is None:
        raise AppValidationError.single("episode_id", "not_found", "Episode not found.", status_code=status.HTTP_404_NOT_FOUND)
    db.delete(episode)
    db.commit()
