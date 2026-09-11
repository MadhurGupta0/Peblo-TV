from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.core.database import get_db
from app.core.errors import AppValidationError
from app.models.episode import Episode
from app.models.enums import PublishStatus, UserRole
from app.models.season import Season
from app.models.show import Show
from app.schemas.common import Page
from app.schemas.show import ShowCreate, ShowOut, ShowUpdate
from app.services.publish_rules import assert_show_publishable

router = APIRouter(prefix="/shows", tags=["shows"])

_editor_or_admin = require_role(UserRole.editor, UserRole.admin)


@router.get("", response_model=Page[ShowOut])
def list_shows(
    section: str | None = Query(default=None),
    status_: PublishStatus | None = Query(default=None, alias="status"),
    language: str | None = Query(default=None),
    q: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _user=Depends(_editor_or_admin),
) -> Page:
    stmt = select(Show)
    if section is not None:
        stmt = stmt.where(Show.section == section)
    if status_ is not None:
        stmt = stmt.where(Show.status == status_)
    if language is not None:
        stmt = stmt.join(Season, Season.show_id == Show.id).join(Episode, Episode.season_id == Season.id).where(Episode.language == language)
    if q:
        stmt = stmt.where(or_(Show.title.ilike(f"%{q}%"), Show.synopsis.ilike(f"%{q}%")))

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(stmt.distinct().order_by(Show.title, Show.id).offset((page - 1) * page_size).limit(page_size)).scalars().all()
    return Page(items=[ShowOut.model_validate(r) for r in rows], total=total, page=page, page_size=page_size)


@router.get("/{show_id}", response_model=ShowOut)
def get_show(show_id: int, db: Session = Depends(get_db), _user=Depends(_editor_or_admin)) -> Show:
    show = db.get(Show, show_id)
    if show is None:
        raise AppValidationError.single("show_id", "not_found", "Show not found.", status_code=status.HTTP_404_NOT_FOUND)
    return show


@router.post("", response_model=ShowOut, status_code=status.HTTP_201_CREATED)
def create_show(body: ShowCreate, db: Session = Depends(get_db), _user=Depends(_editor_or_admin)) -> Show:
    show = Show(**body.model_dump())
    if show.status == PublishStatus.published:
        assert_show_publishable(show)
    db.add(show)
    db.commit()
    db.refresh(show)
    return show


@router.patch("/{show_id}", response_model=ShowOut)
def update_show(show_id: int, body: ShowUpdate, db: Session = Depends(get_db), _user=Depends(_editor_or_admin)) -> Show:
    show = db.get(Show, show_id)
    if show is None:
        raise AppValidationError.single("show_id", "not_found", "Show not found.", status_code=status.HTTP_404_NOT_FOUND)

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(show, field, value)

    if show.status == PublishStatus.published:
        assert_show_publishable(show)

    db.commit()
    db.refresh(show)
    return show


@router.delete("/{show_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_show(show_id: int, db: Session = Depends(get_db), _user=Depends(_editor_or_admin)) -> None:
    show = db.get(Show, show_id)
    if show is None:
        raise AppValidationError.single("show_id", "not_found", "Show not found.", status_code=status.HTTP_404_NOT_FOUND)
    db.delete(show)
    db.commit()
