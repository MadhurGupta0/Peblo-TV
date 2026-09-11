import json

from app.services.catalog_builder import build_catalogue_content
from app.services.publish_job import _canonical_json_bytes
from app.storage.local import LocalDiskStorage
from tests.test_publish_job import _seed_publishable_show


def test_same_db_state_produces_byte_identical_output(db_session, tmp_path):
    _seed_publishable_show(db_session)
    storage = LocalDiskStorage(root=str(tmp_path), public_base_url="http://example.test/storage")

    content_a, counts_a = build_catalogue_content(db_session, storage)
    content_b, counts_b = build_catalogue_content(db_session, storage)

    bytes_a = _canonical_json_bytes(content_a)
    bytes_b = _canonical_json_bytes(content_b)

    assert bytes_a == bytes_b  # byte-for-byte, not just structurally equal
    assert counts_a == counts_b
    # Sanity: it's not trivially empty/degenerate
    assert json.loads(bytes_a)["sections"]
