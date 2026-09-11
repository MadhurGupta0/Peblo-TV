import datetime as dt
import hashlib
import json

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppValidationError
from app.models.enums import PublishRunStatus
from app.models.publish_run import PublishRun
from app.services.catalog_builder import build_catalogue_content
from app.services.catalog_cache import CURRENT_POINTER_KEY, catalog_cache
from app.storage import Storage

SCHEMA_VERSION = 1


def _canonical_json_bytes(obj: dict) -> bytes:
    # sort_keys makes this independent of dict construction order — the same DB state
    # must byte-for-byte produce the same file, and dict insertion order isn't a
    # reliable proxy for "same content" across process runs.
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def _acquire_run(db: Session, actor_user_id: int) -> PublishRun:
    run = PublishRun(
        actor_user_id=actor_user_id,
        started_at=dt.datetime.now(dt.timezone.utc),
        status=PublishRunStatus.running,
        counts={},
    )
    db.add(run)
    try:
        db.commit()
    except IntegrityError:
        # The partial unique index on publish_runs(status) WHERE status='running' is what
        # actually enforces "only one publish in flight" — this is just translating that
        # DB-level rejection into the API's error envelope.
        db.rollback()
        raise AppValidationError.single(
            "_", "publish_in_progress", "A publish is already running. Try again shortly.", status_code=409
        ) from None
    db.refresh(run)
    return run


def run_publish(db: Session, storage: Storage, actor_user_id: int) -> PublishRun:
    run = _acquire_run(db, actor_user_id)

    try:
        content, counts = build_catalogue_content(db, storage)
        checksum = hashlib.sha256(_canonical_json_bytes(content)).hexdigest()
        payload = {
            "schema_version": SCHEMA_VERSION,
            "run_id": run.id,
            "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "checksum": checksum,
            **content,
        }
        run_key = f"catalog/runs/{run.id}.json"
        storage.put(run_key, _canonical_json_bytes(payload), "application/json")

        # Flip the pointer only after the versioned file is fully written. Storage.put
        # itself writes via temp-file + atomic rename, so a reader resolving the pointer
        # never observes a half-written file at either key.
        pointer = {"run_id": run.id, "key": run_key}
        storage.put(CURRENT_POINTER_KEY, _canonical_json_bytes(pointer), "application/json")

        run.status = PublishRunStatus.success
        run.finished_at = dt.datetime.now(dt.timezone.utc)
        run.counts = counts
        run.catalogue_key = run_key
        run.checksum = checksum
        db.commit()
        catalog_cache.set(payload)  # no need to re-read from storage — we already have it
    except Exception as exc:
        db.rollback()
        run = db.get(PublishRun, run.id)
        run.status = PublishRunStatus.failed
        run.finished_at = dt.datetime.now(dt.timezone.utc)
        run.error = str(exc)[:2000]
        db.commit()
        raise

    db.refresh(run)
    return run


def reap_orphaned_runs(db: Session) -> int:
    """Call on process startup. A run stuck at status='running' with no process alive to
    finish it means the previous process died mid-publish — the pointer still names the
    last successful run (never touched), so readers were never affected; this just closes
    out the bookkeeping so /admin/validation-report and run history don't show a run that
    will never complete."""
    orphans = db.execute(select(PublishRun).where(PublishRun.status == PublishRunStatus.running)).scalars().all()
    now = dt.datetime.now(dt.timezone.utc)
    for run in orphans:
        run.status = PublishRunStatus.failed
        run.finished_at = now
        run.error = "process died"
    if orphans:
        db.commit()
    return len(orphans)
