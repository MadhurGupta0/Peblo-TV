from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.core.database import get_db
from app.core.errors import AppValidationError
from app.models.enums import UserRole
from app.models.publish_run import PublishRun
from app.models.user import User
from app.services.publish_job import run_publish
from app.services.validation_report import build_validation_report
from app.storage import get_storage

router = APIRouter(prefix="/admin", tags=["admin"])


def _run_out(run: PublishRun, actor_email: str | None) -> dict:
    duration_seconds = None
    if run.finished_at is not None:
        duration_seconds = (run.finished_at - run.started_at).total_seconds()
    return {
        "run_id": run.id,
        "actor_email": actor_email,
        "status": run.status.value,
        "counts": run.counts,
        "catalogue_key": run.catalogue_key,
        "checksum": run.checksum,
        "error": run.error,
        "started_at": run.started_at.isoformat(),
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "duration_seconds": duration_seconds,
    }


@router.post("/catalog/publish", status_code=status.HTTP_200_OK)
def publish_catalog(db: Session = Depends(get_db), user: User = Depends(require_role(UserRole.admin))) -> dict:
    storage = get_storage()
    try:
        run = run_publish(db, storage, user.id)
    except AppValidationError:
        raise
    except Exception as exc:
        raise AppValidationError.single(
            "_", "publish_failed", f"Publish failed: {exc}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        ) from None

    return _run_out(run, user.email)


@router.get("/validation-report")
def validation_report(
    db: Session = Depends(get_db), _user: User = Depends(require_role(UserRole.editor, UserRole.admin))
) -> dict:
    return build_validation_report(db)


@router.get("/publish-runs")
def list_publish_runs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _user: User = Depends(require_role(UserRole.editor, UserRole.admin)),
) -> dict:
    runs = (
        db.execute(
            select(PublishRun).order_by(PublishRun.started_at.desc()).offset((page - 1) * page_size).limit(page_size)
        )
        .scalars()
        .all()
    )
    actor_ids = {r.actor_user_id for r in runs}
    emails = {}
    if actor_ids:
        for u in db.execute(select(User).where(User.id.in_(actor_ids))).scalars():
            emails[u.id] = u.email

    total = db.execute(select(func.count()).select_from(PublishRun)).scalar_one()
    return {
        "items": [_run_out(r, emails.get(r.actor_user_id)) for r in runs],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
