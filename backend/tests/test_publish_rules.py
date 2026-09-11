import pytest

from tests.conftest import ADMIN_PASSWORD, EDITOR_PASSWORD, auth_header


@pytest.fixture
def editor_headers(client, editor_user):
    return auth_header(client, editor_user.email, EDITOR_PASSWORD)


@pytest.fixture
def admin_headers(client, admin_user):
    return auth_header(client, admin_user.email, ADMIN_PASSWORD)


def test_episode_cannot_publish_without_duration_or_artwork(client, editor_headers, season):
    resp = client.post(
        "/episodes",
        headers=editor_headers,
        json={"season_id": season.id, "episode_number": 1, "title": "Ep 1", "language": "en", "status": "published"},
    )
    assert resp.status_code == 422, resp.text
    codes = {e["code"] for e in resp.json()["errors"]}
    assert codes == {"missing_duration", "missing_artwork"}


def test_episode_can_publish_with_duration_and_artwork(client, editor_headers, admin_headers, season):
    resp = client.post(
        "/episodes",
        headers=editor_headers,
        json={"season_id": season.id, "episode_number": 1, "title": "Ep 1", "language": "en", "duration_seconds": 300},
    )
    assert resp.status_code == 201, resp.text
    episode_id = resp.json()["id"]

    from pathlib import Path

    thumb = (Path(__file__).resolve().parent.parent.parent / "_given" / "assets" / "thumb_tiny.jpg").read_bytes()
    resp = client.post(
        "/admin/artwork",
        headers=admin_headers,
        data={"kind": "thumbnail", "owner_type": "episode", "owner_id": episode_id},
        files={"file": ("thumb.jpg", thumb, "image/jpeg")},
    )
    assert resp.status_code == 201, resp.text

    resp = client.patch(f"/episodes/{episode_id}", headers=editor_headers, json={"status": "published"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "published"


def test_show_cannot_publish_without_section(client, editor_headers):
    resp = client.post(
        "/shows",
        headers=editor_headers,
        json={"slug": "no-section-show", "title": "No Section Show", "section": None, "status": "published"},
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["errors"][0]["code"] == "missing_section"


def test_show_can_publish_with_section(client, editor_headers):
    resp = client.post(
        "/shows",
        headers=editor_headers,
        json={"slug": "sectioned-show", "title": "Sectioned Show", "section": "series", "status": "published"},
    )
    assert resp.status_code == 201, resp.text
