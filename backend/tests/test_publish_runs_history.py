from tests.conftest import ADMIN_PASSWORD, EDITOR_PASSWORD, auth_header
from tests.test_publish_job import _seed_publishable_show


def test_publish_run_history_lists_runs_with_actor_and_duration(client, admin_user, editor_user, db_session):
    _seed_publishable_show(db_session)
    admin_headers = auth_header(client, admin_user.email, ADMIN_PASSWORD)
    assert client.post("/admin/catalog/publish", headers=admin_headers).status_code == 200

    editor_headers = auth_header(client, editor_user.email, EDITOR_PASSWORD)
    resp = client.get("/admin/publish-runs", headers=editor_headers)  # editor can view, not just admin
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 1
    run = body["items"][0]
    assert run["actor_email"] == admin_user.email
    assert run["status"] == "success"
    assert run["duration_seconds"] is not None


def test_publish_run_history_gated_to_editor_and_admin(client):
    resp = client.get("/admin/publish-runs")
    assert resp.status_code == 401
