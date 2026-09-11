from fastapi import APIRouter, Query, Request, Response, status

from app.services.catalog_cache import catalog_cache

router = APIRouter(tags=["catalog"])

_EMPTY_CATALOG = {"schema_version": 1, "run_id": None, "generated_at": None, "checksum": None, "sections": []}


@router.get("/catalog")
def get_catalog(request: Request, response: Response) -> dict:
    catalog = catalog_cache.get()
    if catalog is None:
        return _EMPTY_CATALOG  # nothing published yet — graceful, not an error

    etag = f'"{catalog["checksum"]}"'
    if request.headers.get("if-none-match") == etag:
        response.status_code = status.HTTP_304_NOT_MODIFIED
        response.headers["ETag"] = etag
        return response

    response.headers["ETag"] = etag
    response.headers["Cache-Control"] = "public, max-age=60"
    return catalog


def _show_matches(show: dict, section: str, category: str | None, language: str | None, q: str | None) -> bool:
    if category is not None and category not in show["categories"]:
        return False

    if language is not None:
        all_episodes = show["trailers"] + [ep for s in show["seasons"] for ep in s["episodes"]]
        if not any(language in ep["languages"] for ep in all_episodes):
            return False

    if q:
        needle = q.lower()
        all_episodes = show["trailers"] + [ep for s in show["seasons"] for ep in s["episodes"]]
        matched = (
            needle in show["title"].lower()
            or any(needle in ep["title"].lower() for ep in all_episodes)
            or any(needle in cat.lower() for cat in show["categories"])
        )
        if not matched:
            return False

    return True


@router.get("/catalog/search")
def search_catalog(
    q: str | None = Query(default=None),
    category: str | None = Query(default=None),
    language: str | None = Query(default=None),
    section: str | None = Query(default=None),
) -> dict:
    catalog = catalog_cache.get() or _EMPTY_CATALOG
    results = []
    for section_group in catalog["sections"]:
        if section is not None and section_group["section"] != section:
            continue
        for show in section_group["shows"]:
            if _show_matches(show, section_group["section"], category, language, q):
                results.append({**show, "section": section_group["section"]})

    return {"shows": results}
