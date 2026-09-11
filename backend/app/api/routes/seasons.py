from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.core.database import get_db
from app.core.errors import AppValidationError
from app.models.enums import UserRole
from app.models.season import Season
from app.models.show import Show
from app.schemas.season import SeasonCreate, SeasonOut, SeasonUpdate

router = APIRouter(tags=["seasons"])

_editor_or_admin = require_role(UserRole.editor, UserRole.admin)


def _get_show_or_404(db: Session, show_id: int) -> Show:
    show = db.get(Show, show_id)
    if show is None:
        raise AppValidationError.single("show_id", "not_found", "Show not found.", status_code=status.HTTP_404_NOT_FOUND)
    return show


@router.get("/shows/{show_id}/seasons", response_model=list[SeasonOut])
def list_seasons(show_id: int, db: Session = Depends(get_db), _user=Depends(_editor_or_admin)) -> list[Season]:
    _get_show_or_404(db, show_id)
    return db.execute(select(Season).where(Season.show_id == show_id).order_by(Season.season_number)).scalars().all()


@router.post("/shows/{show_id}/seasons", response_model=SeasonOut, status_code=status.HTTP_201_CREATED)
def create_season(show_id: int, body: SeasonCreate, db: Session = Depends(get_db), _user=Depends(_editor_or_admin)) -> Season:
    _get_show_or_404(db, show_id)
    season = Season(show_id=show_id, **body.model_dump())
    db.add(season)
    db.commit()
    db.refresh(season)
    return season


@router.patch("/seasons/{season_id}", response_model=SeasonOut)
def update_season(season_id: int, body: SeasonUpdate, db: Session = Depends(get_db), _user=Depends(_editor_or_admin)) -> Season:
    season = db.get(Season, season_id)
    if season is None:
        raise AppValidationError.single("season_id", "not_found", "Season not found.", status_code=status.HTTP_404_NOT_FOUND)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(season, field, value)
    db.commit()
    db.refresh(season)
    return season


@router.delete("/seasons/{season_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_season(season_id: int, db: Session = Depends(get_db), _user=Depends(_editor_or_admin)) -> None:
    season = db.get(Season, season_id)
    if season is None:
        raise AppValidationError.single("season_id", "not_found", "Season not found.", status_code=status.HTTP_404_NOT_FOUND)
    db.delete(season)
    db.commit()
