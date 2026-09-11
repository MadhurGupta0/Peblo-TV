from app.models.enums import PublishStatus
from app.models.episode import Episode
from app.models.season import Season
from app.models.show import Show
from tests.conftest import EDITOR_PASSWORD, auth_header


def _editor_headers(client, editor_user):
    return auth_header(client, editor_user.email, EDITOR_PASSWORD)


def test_report_is_empty_when_nothing_is_broken(client, editor_user, season):
    resp = client.get("/admin/validation-report", headers=_editor_headers(client, editor_user))
    assert resp.status_code == 200
    assert resp.json() == {"shows": [], "total_blocking_issues": 0}


def test_report_catches_published_episode_with_no_artwork_imported_directly(client, editor_user, db_session, season):
    # Mirrors the real seed data's ep_0036 (Discover India with Moti S1E4): a row inserted
    # directly (bypassing API validation, like the seeder does) that is status=published
    # but has no artwork. The API itself would never allow this via POST/PATCH.
    season.show.status = PublishStatus.published  # the report only looks at published shows
    episode = Episode(
        season_id=season.id, episode_number=1, title="No Artwork Ep", language="en",
        duration_seconds=300, status=PublishStatus.published,
    )
    db_session.add(episode)
    db_session.commit()

    resp = client.get("/admin/validation-report", headers=_editor_headers(client, editor_user))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total_blocking_issues"] == 1
    show_report = body["shows"][0]
    assert show_report["episodes"][0]["issues"][0]["code"] == "missing_artwork"


def test_report_catches_published_show_with_no_section(client, editor_user, db_session):
    show = Show(slug="no-section", title="No Section Show", section=None, categories=[], status=PublishStatus.published)
    db_session.add(show)
    db_session.commit()

    resp = client.get("/admin/validation-report", headers=_editor_headers(client, editor_user))
    assert resp.status_code == 200
    body = resp.json()
    matching = [s for s in body["shows"] if s["slug"] == "no-section"]
    assert len(matching) == 1
    assert matching[0]["issues"][0]["code"] == "missing_section"


def test_report_gated_to_editor_and_admin(client):
    resp = client.get("/admin/validation-report")
    assert resp.status_code == 401
