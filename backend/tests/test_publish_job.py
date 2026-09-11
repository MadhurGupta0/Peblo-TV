import json
from pathlib import Path

import pytest

from app.models.artwork import Artwork
from app.models.enums import ArtworkKind, ArtworkOwnerType, PublishStatus
from app.models.episode import Episode
from app.models.publish_run import PublishRun
from app.models.season import Season
from app.models.show import Show
from app.storage import get_storage
from tests.conftest import ADMIN_PASSWORD, auth_header

ASSETS = Path(__file__).resolve().parent.parent.parent / "_given" / "assets"


@pytest.fixture
def admin_headers(client, admin_user):
    return auth_header(client, admin_user.email, ADMIN_PASSWORD)


def _thumb_bytes() -> bytes:
    return (ASSETS / "thumb_tiny.jpg").read_bytes()


def _seed_publishable_show(db_session):
    show = Show(
        slug="publishable-show",
        title="Publishable Show",
        synopsis="A show ready to publish.",
        section="series",
        categories=["stories"],
        status=PublishStatus.published,
    )
    db_session.add(show)
    db_session.flush()

    season0 = Season(show_id=show.id, season_number=0)
    season1 = Season(show_id=show.id, season_number=1)
    db_session.add_all([season0, season1])
    db_session.flush()

    trailer = Episode(
        season_id=season0.id, episode_number=1, title="Trailer", language="en",
        duration_seconds=60, status=PublishStatus.published,
    )
    ep1_en = Episode(
        season_id=season1.id, episode_number=1, title="Ep One", language="en",
        duration_seconds=300, content_group="pub-show-s01e01", status=PublishStatus.published,
    )
    ep1_hi = Episode(
        season_id=season1.id, episode_number=1, title="Ep One (Hindi)", language="hi",
        duration_seconds=310, content_group="pub-show-s01e01", status=PublishStatus.published,
    )
    ep2_draft = Episode(
        season_id=season1.id, episode_number=2, title="Ep Two", language="en",
        duration_seconds=300, status=PublishStatus.draft,
    )
    db_session.add_all([trailer, ep1_en, ep1_hi, ep2_draft])
    db_session.flush()

    for episode in (trailer, ep1_en, ep1_hi):
        db_session.add(
            Artwork(
                owner_type=ArtworkOwnerType.episode,
                owner_id=episode.id,
                kind=ArtworkKind.thumbnail,
                storage_key=f"artwork/episode/{episode.id}/thumbnail.jpg",
                width=640,
                height=360,
                bytes=1234,
                content_type="image/jpeg",
                checksum="deadbeef",
            )
        )
    db_session.commit()
    db_session.refresh(show)
    return show


def _seed_draft_only_show(db_session):
    """A published show with zero publishable episodes — must be dropped entirely."""
    show = Show(slug="empty-show", title="Empty Show", section="series", categories=[], status=PublishStatus.published)
    db_session.add(show)
    db_session.flush()
    season = Season(show_id=show.id, season_number=1)
    db_session.add(season)
    db_session.flush()
    db_session.add(Episode(season_id=season.id, episode_number=1, title="Draft only", language="en", status=PublishStatus.draft))
    db_session.commit()
    return show


def test_publish_builds_expected_structure_and_records_run(client, admin_headers, db_session):
    _seed_publishable_show(db_session)
    _seed_draft_only_show(db_session)

    resp = client.post("/admin/catalog/publish", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "success"
    assert body["counts"] == {"shows": 1, "episodes": 2, "sections": 1}  # empty-show dropped; trailer + 1 collapsed episode

    run_row = db_session.get(PublishRun, body["run_id"])
    assert run_row.status.value == "success"
    assert run_row.catalogue_key == f"catalog/runs/{body['run_id']}.json"

    storage = get_storage()
    pointer = json.loads(storage.get("catalog/current.json"))
    assert pointer == {"run_id": body["run_id"], "key": run_row.catalogue_key}

    catalogue = json.loads(storage.get(run_row.catalogue_key))
    assert catalogue["schema_version"] == 1
    assert catalogue["checksum"] == body["checksum"]
    assert len(catalogue["sections"]) == 1
    section = catalogue["sections"][0]
    assert section["section"] == "series"
    assert len(section["shows"]) == 1  # empty-show excluded

    show_entry = section["shows"][0]
    assert show_entry["slug"] == "publishable-show"
    assert len(show_entry["trailers"]) == 1
    assert show_entry["trailers"][0]["title"] == "Trailer"
    assert len(show_entry["seasons"]) == 1  # season 0 is not a normal season
    assert show_entry["seasons"][0]["season_number"] == 1

    episodes = show_entry["seasons"][0]["episodes"]
    assert len(episodes) == 1  # en+hi variants of episode 1 collapsed into one entry
    entry = episodes[0]
    assert entry["languages"] == ["en", "hi"]
    assert entry["title"] == "Ep One"  # "en" is alphabetically first -> canonical


def test_publish_is_idempotent_on_unchanged_data(client, admin_headers, db_session):
    _seed_publishable_show(db_session)

    first = client.post("/admin/catalog/publish", headers=admin_headers).json()
    second = client.post("/admin/catalog/publish", headers=admin_headers).json()

    assert first["checksum"] == second["checksum"]
    assert first["run_id"] != second["run_id"]  # still recorded as two distinct runs

    storage = get_storage()
    pointer = json.loads(storage.get("catalog/current.json"))
    assert pointer["run_id"] == second["run_id"]  # pointer always resolves to the latest run


def test_concurrent_publish_returns_409(client, admin_headers, db_session, admin_user):
    # Simulate an in-flight publish from another request by inserting the 'running' row
    # directly — this is exactly the state the partial unique index is designed to catch.
    import datetime as dt

    from app.models.enums import PublishRunStatus

    db_session.add(
        PublishRun(actor_user_id=admin_user.id, started_at=dt.datetime.now(dt.timezone.utc), status=PublishRunStatus.running, counts={})
    )
    db_session.commit()

    resp = client.post("/admin/catalog/publish", headers=admin_headers)
    assert resp.status_code == 409
    assert resp.json()["errors"][0]["code"] == "publish_in_progress"


def test_startup_reaper_marks_orphaned_running_runs_as_failed(db_session):
    import datetime as dt

    from app.models.enums import PublishRunStatus
    from app.services.publish_job import reap_orphaned_runs

    orphan = PublishRun(actor_user_id=1, started_at=dt.datetime.now(dt.timezone.utc), status=PublishRunStatus.running, counts={})
    db_session.add(orphan)
    db_session.commit()
    db_session.refresh(orphan)

    reaped = reap_orphaned_runs(db_session)
    assert reaped == 1

    db_session.refresh(orphan)
    assert orphan.status == PublishRunStatus.failed
    assert orphan.error == "process died"
