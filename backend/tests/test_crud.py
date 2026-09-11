import pytest

from tests.conftest import EDITOR_PASSWORD, auth_header


@pytest.fixture
def editor_headers(client, editor_user):
    return auth_header(client, editor_user.email, EDITOR_PASSWORD)


def test_show_crud_roundtrip(client, editor_headers):
    resp = client.post(
        "/shows",
        headers=editor_headers,
        json={"slug": "new-show", "title": "New Show", "section": "series", "categories": ["stories"]},
    )
    assert resp.status_code == 201, resp.text
    show_id = resp.json()["id"]

    resp = client.get(f"/shows/{show_id}", headers=editor_headers)
    assert resp.status_code == 200
    assert resp.json()["title"] == "New Show"

    resp = client.patch(f"/shows/{show_id}", headers=editor_headers, json={"title": "Renamed Show"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "Renamed Show"

    resp = client.delete(f"/shows/{show_id}", headers=editor_headers)
    assert resp.status_code == 204

    resp = client.get(f"/shows/{show_id}", headers=editor_headers)
    assert resp.status_code == 404


def test_show_list_is_gated_to_editor_and_admin(client):
    resp = client.get("/shows")
    assert resp.status_code == 401


def test_show_filters_compose_including_language(client, editor_headers, db_session, show):
    from app.models.enums import PublishStatus
    from app.models.episode import Episode
    from app.models.season import Season
    from app.models.show import Show

    second_show = Show(slug="hindi-show", title="Hindi Songs", section="songs", categories=["songs"], status=PublishStatus.draft)
    db_session.add(second_show)
    db_session.flush()

    season_one = Season(show_id=show.id, season_number=1, title=None)
    season_two = Season(show_id=second_show.id, season_number=1, title=None)
    db_session.add_all([season_one, season_two])
    db_session.flush()

    db_session.add_all(
        [
            Episode(season_id=season_one.id, episode_number=1, title="English Episode", language="en", status=PublishStatus.draft),
            Episode(season_id=season_two.id, episode_number=1, title="Hindi Episode", language="hi", status=PublishStatus.draft),
        ]
    )
    db_session.commit()

    def titles(**params):
        resp = client.get("/shows", headers=editor_headers, params=params)
        assert resp.status_code == 200, resp.text
        return {item["title"] for item in resp.json()["items"]}

    assert titles(language="en") == {"Test Show"}
    assert titles(language="hi") == {"Hindi Songs"}
    assert titles(section="songs", language="hi", q="Hindi") == {"Hindi Songs"}
    assert titles(section="series", language="hi") == set()


def test_season_and_episode_crud_roundtrip(client, editor_headers, show):
    resp = client.post(f"/shows/{show.id}/seasons", headers=editor_headers, json={"season_number": 1})
    assert resp.status_code == 201, resp.text
    season_id = resp.json()["id"]

    resp = client.post(
        "/episodes",
        headers=editor_headers,
        json={"season_id": season_id, "episode_number": 1, "title": "Ep 1", "language": "en"},
    )
    assert resp.status_code == 201, resp.text
    episode_id = resp.json()["id"]

    resp = client.patch(f"/episodes/{episode_id}", headers=editor_headers, json={"title": "Ep 1 renamed"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "Ep 1 renamed"

    resp = client.delete(f"/episodes/{episode_id}", headers=editor_headers)
    assert resp.status_code == 204


def test_content_group_language_conflict_returns_409(client, editor_headers, season):
    body = {
        "season_id": season.id,
        "episode_number": 1,
        "title": "Ep 1",
        "language": "en",
        "content_group": "shared-group",
    }
    resp = client.post("/episodes", headers=editor_headers, json=body)
    assert resp.status_code == 201, resp.text

    conflict_body = {**body, "episode_number": 2}  # different episode_number, same (content_group, language)
    resp = client.post("/episodes", headers=editor_headers, json=conflict_body)
    assert resp.status_code == 409
    assert resp.json()["errors"][0]["code"] == "conflict"


def test_episode_filters_compose(client, editor_headers, db_session, season):
    # Seeded directly via the DB session, bypassing the API's publish-rule checks (§2.5's
    # own "episode can't publish without artwork+duration" rule, proven separately in
    # test_publish_rules.py) — this test is only about filter composition on /episodes.
    from app.models.enums import PublishStatus
    from app.models.episode import Episode

    rows = [
        Episode(season_id=season.id, episode_number=1, title="Alpha Adventure", language="en", status=PublishStatus.published),
        Episode(season_id=season.id, episode_number=2, title="Beta Story", language="hi", status=PublishStatus.draft),
        Episode(season_id=season.id, episode_number=3, title="Alpha Returns", language="hi", status=PublishStatus.published),
    ]
    db_session.add_all(rows)
    db_session.commit()

    def titles(**params):
        resp = client.get("/episodes", headers=editor_headers, params=params)
        assert resp.status_code == 200, resp.text
        return {item["title"] for item in resp.json()["items"]}

    assert titles(section="series") == {"Alpha Adventure", "Beta Story", "Alpha Returns"}
    assert titles(status="published") == {"Alpha Adventure", "Alpha Returns"}
    assert titles(language="hi") == {"Beta Story", "Alpha Returns"}
    assert titles(q="Alpha") == {"Alpha Adventure", "Alpha Returns"}
    # all four compose with AND semantics
    assert titles(section="series", status="published", language="hi", q="Alpha") == {"Alpha Returns"}
    assert titles(section="series", status="draft", language="hi", q="Alpha") == set()
