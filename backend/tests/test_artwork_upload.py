import io
from pathlib import Path

import pytest
from PIL import Image

from tests.conftest import ADMIN_PASSWORD, auth_header

ASSETS = Path(__file__).resolve().parent.parent.parent / "_given" / "assets"


def _upload(client, headers, show, kind, filename):
    data = (ASSETS / filename).read_bytes()
    resp = client.post(
        "/admin/artwork",
        headers=headers,
        data={"kind": kind, "owner_type": "show", "owner_id": show.id},
        files={"file": (filename, data, "application/octet-stream")},
    )
    return resp


@pytest.fixture
def admin_headers(client, admin_user):
    return auth_header(client, admin_user.email, ADMIN_PASSWORD)


def test_poster_good_accepted(client, admin_headers, show):
    resp = _upload(client, admin_headers, show, "poster", "poster_good.jpg")
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["width"] == 600 and body["height"] == 900


def test_banner_good_accepted(client, admin_headers, show):
    resp = _upload(client, admin_headers, show, "banner", "banner_good.jpg")
    assert resp.status_code == 201, resp.text


def test_thumb_640x360_accepted(client, admin_headers, show):
    # thumb_tiny.jpg is actually 640x360 (matches the thumbnail target exactly) despite its
    # name — see docs/DATA_FINDINGS.md. Validation goes by decoded pixels, never filenames.
    resp = _upload(client, admin_headers, show, "thumbnail", "thumb_tiny.jpg")
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["width"] == 640 and body["height"] == 360


def test_poster_wrong_ratio_rejected_as_aspect_error(client, admin_headers, show):
    resp = _upload(client, admin_headers, show, "poster", "poster_wrong_ratio.jpg")
    assert resp.status_code == 422
    errors = resp.json()["errors"]
    assert errors[0]["code"] == "aspect_mismatch"


def test_banner_too_big_rejected_as_size_error(client, admin_headers, show):
    resp = _upload(client, admin_headers, show, "banner", "banner_too_big.png")
    assert resp.status_code == 422
    errors = resp.json()["errors"]
    assert errors[0]["code"] == "size_too_large"


def test_thumb_160x90_rejected_as_dimension_error(client, admin_headers, show):
    # thumb_good.jpg is actually 160x90 — correct 16:9 aspect but a quarter of the
    # 640x360 target, outside the [80%, 130%] dimension band. Name notwithstanding.
    resp = _upload(client, admin_headers, show, "thumbnail", "thumb_good.jpg")
    assert resp.status_code == 422
    errors = resp.json()["errors"]
    assert errors[0]["code"] == "dimension_out_of_range"


def test_list_artwork_for_owner_returns_uploaded_assets(client, admin_headers, show):
    poster = _upload(client, admin_headers, show, "poster", "poster_good.jpg")
    banner = _upload(client, admin_headers, show, "banner", "banner_good.jpg")
    assert poster.status_code == 201, poster.text
    assert banner.status_code == 201, banner.text

    resp = client.get(f"/admin/artwork?owner_type=show&owner_id={show.id}", headers=admin_headers)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert [item["kind"] for item in body] == ["banner", "poster"]
    assert all(item["owner_type"] == "show" for item in body)
    assert all(item["owner_id"] == show.id for item in body)


def _jpeg_of_size(width: int, height: int, target_bytes: int) -> bytes:
    img = Image.new("RGB", (width, height), color=(120, 140, 160))
    quality = 95
    while quality > 5:
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality)
        if buf.tell() <= target_bytes:
            return buf.getvalue()
        quality -= 5
    return buf.getvalue()


def test_boundary_199kb_accepted(client, admin_headers, show):
    data = _jpeg_of_size(600, 900, 199 * 1024)
    assert len(data) <= 199 * 1024
    resp = client.post(
        "/admin/artwork",
        headers=admin_headers,
        data={"kind": "poster", "owner_type": "show", "owner_id": show.id},
        files={"file": ("boundary_199.jpg", data, "image/jpeg")},
    )
    assert resp.status_code == 201, resp.text


def _com_marker(payload: bytes) -> bytes:
    # JPEG COM marker segment: 0xFFFE, 2-byte length (including itself), payload.
    # Max payload per segment is 65533 bytes, so large padding needs multiple segments.
    return b"\xff\xfe" + (len(payload) + 2).to_bytes(2, "big") + payload


def test_boundary_201kb_rejected(client, admin_headers, show):
    # Pad a valid under-limit JPEG with harmless COM marker segments to push it just over
    # 200KB while keeping it a valid, decodable image — isolates the size check from aspect/dimension.
    base = _jpeg_of_size(600, 900, 150 * 1024)
    padding_needed = (201 * 1024) - len(base)
    markers = b""
    remaining = padding_needed
    while remaining > 0:
        chunk = min(remaining, 65000)
        markers += _com_marker(b"0" * chunk)
        remaining -= chunk
    padded = base[:2] + markers + base[2:]
    assert len(padded) > 200 * 1024
    resp = client.post(
        "/admin/artwork",
        headers=admin_headers,
        data={"kind": "poster", "owner_type": "show", "owner_id": show.id},
        files={"file": ("boundary_201.jpg", padded, "image/jpeg")},
    )
    assert resp.status_code == 422
    errors = resp.json()["errors"]
    assert errors[0]["code"] == "size_too_large"
