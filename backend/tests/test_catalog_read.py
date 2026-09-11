from tests.conftest import ADMIN_PASSWORD, auth_header
from tests.test_publish_job import _seed_publishable_show


def _admin_headers(client, admin_user):
    return auth_header(client, admin_user.email, ADMIN_PASSWORD)


def test_catalog_returns_empty_placeholder_before_any_publish(client):
    resp = client.get("/catalog")
    assert resp.status_code == 200
    assert resp.json()["sections"] == []
    assert resp.json()["run_id"] is None


def test_catalog_reflects_published_data_with_etag(client, admin_user, db_session):
    _seed_publishable_show(db_session)
    headers = _admin_headers(client, admin_user)
    publish_resp = client.post("/admin/catalog/publish", headers=headers)
    assert publish_resp.status_code == 200, publish_resp.text

    resp = client.get("/catalog")
    assert resp.status_code == 200
    assert "etag" in {k.lower() for k in resp.headers}
    assert len(resp.json()["sections"]) == 1

    etag = resp.headers["etag"]
    resp2 = client.get("/catalog", headers={"if-none-match": etag})
    assert resp2.status_code == 304


def test_search_filters_compose(client, admin_user, db_session):
    _seed_publishable_show(db_session)
    headers = _admin_headers(client, admin_user)
    assert client.post("/admin/catalog/publish", headers=headers).status_code == 200

    def titles(**params):
        resp = client.get("/catalog/search", params=params)
        assert resp.status_code == 200, resp.text
        return {s["title"] for s in resp.json()["shows"]}

    assert titles() == {"Publishable Show"}
    assert titles(section="series") == {"Publishable Show"}
    assert titles(section="songs") == set()
    assert titles(category="stories") == {"Publishable Show"}
    assert titles(category="nature") == set()
    assert titles(language="hi") == {"Publishable Show"}  # Ep One has an hi variant
    assert titles(language="fr") == set()
    assert titles(q="ep one") == {"Publishable Show"}  # matches episode title
    assert titles(q="stories") == {"Publishable Show"}  # matches category text
    assert titles(q="nonexistent") == set()
    # all four together (AND across filters)
    assert titles(section="series", category="stories", language="hi", q="ep one") == {"Publishable Show"}
    assert titles(section="series", category="stories", language="hi", q="nonexistent") == set()
