from tests.conftest import ADMIN_PASSWORD, EDITOR_PASSWORD, auth_header


def test_anon_gets_401_on_publish(client):
    resp = client.post("/admin/catalog/publish")
    assert resp.status_code == 401


def test_editor_gets_403_on_publish(client, editor_user):
    headers = auth_header(client, editor_user.email, EDITOR_PASSWORD)
    resp = client.post("/admin/catalog/publish", headers=headers)
    assert resp.status_code == 403


def test_admin_is_allowed_past_role_check_on_publish(client, admin_user):
    headers = auth_header(client, admin_user.email, ADMIN_PASSWORD)
    resp = client.post("/admin/catalog/publish", headers=headers)
    # Role check passes for admin; an empty catalogue (no published shows) is still a
    # valid, successful publish — see test_publish_job.py for the full build/atomicity story.
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "success"


def test_anon_gets_200_on_catalog(client):
    resp = client.get("/catalog")
    assert resp.status_code == 200


def test_login_rejects_wrong_password(client, editor_user):
    resp = client.post("/auth/login", json={"email": editor_user.email, "password": "wrong"})
    assert resp.status_code == 401


def test_me_reflects_logged_in_role(client, admin_user):
    headers = auth_header(client, admin_user.email, ADMIN_PASSWORD)
    resp = client.get("/auth/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["role"] == "admin"
