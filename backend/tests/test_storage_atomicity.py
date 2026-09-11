import os

import pytest

from app.storage.local import LocalDiskStorage


def test_failed_write_never_leaves_a_partial_file_at_the_target_path(tmp_path, monkeypatch):
    storage = LocalDiskStorage(root=str(tmp_path), public_base_url="http://example.test/storage")
    storage.put("catalog/current.json", b'{"run_id": 1, "key": "catalog/runs/1.json"}', "application/json")

    original_bytes = storage.get("catalog/current.json")

    def _boom(*args, **kwargs):
        raise OSError("simulated crash during atomic rename")

    monkeypatch.setattr(os, "replace", _boom)

    with pytest.raises(OSError):
        storage.put("catalog/current.json", b'{"run_id": 2, "key": "catalog/runs/2.json"}', "application/json")

    # The pointer must still name the last good run — a reader must never see a
    # half-written file, and a failed write must not touch the previously-good one.
    assert storage.get("catalog/current.json") == original_bytes

    # No stray temp file left behind in the target directory.
    leftovers = [p for p in (tmp_path / "catalog").iterdir() if p.name != "current.json"]
    assert leftovers == []


def test_write_to_a_new_key_leaves_nothing_behind_on_failure(tmp_path, monkeypatch):
    storage = LocalDiskStorage(root=str(tmp_path), public_base_url="http://example.test/storage")

    def _boom(*args, **kwargs):
        raise OSError("simulated crash during atomic rename")

    monkeypatch.setattr(os, "replace", _boom)

    with pytest.raises(OSError):
        storage.put("catalog/runs/1.json", b"{}", "application/json")

    assert not storage.exists("catalog/runs/1.json")
    assert list((tmp_path / "catalog" / "runs").iterdir()) == []
