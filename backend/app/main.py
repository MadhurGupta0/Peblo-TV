from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.api.routes import admin, artwork, auth, catalog, episodes, seasons, shows
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.errors import (
    AppValidationError,
    app_validation_error_handler,
    integrity_error_handler,
    request_validation_error_handler,
)
from app.models import PublishRun
from app.services.catalog_cache import catalog_cache
from app.services.publish_job import reap_orphaned_runs
from app.storage import get_storage

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # A run stuck at status='running' means the previous process died mid-publish. The
    # catalogue pointer was never touched by that run, so this is bookkeeping cleanup
    # (closing out publish_runs/history), not a correctness fix.
    with SessionLocal() as db:
        reap_orphaned_runs(db)
    # Warm the in-memory catalogue cache from whatever was last published — GET /catalog
    # and /catalog/search never hit the DB, so without this a fresh process would 404/empty
    # until the next publish even though a perfectly good catalogue already exists.
    catalog_cache.refresh_from_storage(get_storage())
    yield


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_exception_handler(AppValidationError, app_validation_error_handler)
app.add_exception_handler(RequestValidationError, request_validation_error_handler)
app.add_exception_handler(IntegrityError, integrity_error_handler)

if settings.storage_backend == "local":
    app.mount("/storage", StaticFiles(directory=settings.storage_local_path), name="storage")

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(artwork.router)
app.include_router(catalog.router)
app.include_router(shows.router)
app.include_router(seasons.router)
app.include_router(episodes.router)


@app.get("/health")
def health() -> dict:
    db_ok = True
    last_run_id = None
    db_error = None
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
            last_run = db.execute(select(PublishRun).order_by(PublishRun.id.desc()).limit(1)).scalar_one_or_none()
            last_run_id = last_run.id if last_run else None
    except Exception as exc:
        db_ok = False
        db_error = str(exc)

    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "database": "ok" if db_ok else "unreachable",
        "database_error": db_error,
        "storage_backend": settings.storage_backend,
        "last_publish_run_id": last_run_id,
    }


@app.get("/endpoints")
def list_endpoints() -> dict:
    routes = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        routes.append(
            {
                "path": route.path,
                "methods": sorted(method for method in route.methods if method not in {"HEAD", "OPTIONS"}),
                "name": route.name,
            }
        )

    routes.sort(key=lambda route: (route["path"], route["methods"], route["name"]))
    return {"endpoints": routes}
