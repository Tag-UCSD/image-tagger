"""Smoke-critical Admin integration tests (Task A-11, A2-4).

Covers the authentication boundary (401 / 403) and basic happy paths for
budget, asynchronous upload, and image-set import. ``get_total_spent`` is
monkeypatched so the test DB does not need a full
:class:`~backend.models.usage.ToolUsage` ledger.
"""

from __future__ import annotations

import io
import uuid

import pytest
from httpx import AsyncClient

from backend.tests.conftest import mint_jwt

# Minimal valid 1x1 PNG (canonical test asset).
_PNG_1X1 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82"
)


@pytest.fixture
def zero_spend(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "backend.services.costs.get_total_spent",
        lambda: 0.0,
    )


@pytest.mark.asyncio
async def test_admin_budget_ok_with_admin_jwt(
    async_client: AsyncClient,
    zero_spend: None,
) -> None:
    resp = await async_client.get(
        "/v1/admin/budget",
        headers={"Authorization": f"Bearer {mint_jwt('admin')}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert set(body.keys()) >= {"total_spent", "hard_limit", "is_kill_switched"}


@pytest.mark.asyncio
async def test_admin_budget_forbidden_for_tagger_jwt(
    async_client: AsyncClient,
    zero_spend: None,
) -> None:
    resp = await async_client.get(
        "/v1/admin/budget",
        headers={"Authorization": f"Bearer {mint_jwt('tagger')}"},
    )
    assert resp.status_code == 403, resp.text
    err = resp.json()["error"]
    assert err["code"] == "FORBIDDEN"
    assert isinstance(err["request_id"], str) and err["request_id"]


@pytest.mark.asyncio
async def test_admin_budget_unauthorized_without_bearer(
    async_client: AsyncClient,
) -> None:
    resp = await async_client.get("/v1/admin/budget")
    assert resp.status_code == 401, resp.text
    err = resp.json()["error"]
    assert err["code"] == "AUTH_REQUIRED"


@pytest.mark.asyncio
async def test_admin_upload_multipart_accepted(
    async_client: AsyncClient,
    zero_spend: None,
) -> None:
    resp = await async_client.post(
        "/v1/admin/upload",
        headers={"Authorization": f"Bearer {mint_jwt('admin')}"},
        files=[("files", ("smoke.png", io.BytesIO(_PNG_1X1), "image/png"))],
    )
    assert resp.status_code == 202, resp.text
    body = resp.json()
    assert body.get("created_count", 0) >= 1
    assert isinstance(body.get("image_ids"), list)
    assert body["image_ids"]
    assert body.get("status") == "queued"
    assert isinstance(body.get("items"), list)
    assert len(body["items"]) >= 1
    assert body["items"][0].get("image_id") == body["image_ids"][0]


@pytest.mark.asyncio
async def test_admin_upload_accepts_files_bracket_field_name(
    async_client: AsyncClient,
    zero_spend: None,
) -> None:
    """Contract field name ``files[]`` must be accepted (frontend uses it)."""
    resp = await async_client.post(
        "/v1/admin/upload",
        headers={"Authorization": f"Bearer {mint_jwt('admin')}"},
        files=[("files[]", ("smoke.png", io.BytesIO(_PNG_1X1), "image/png"))],
    )
    assert resp.status_code == 202, resp.text


def _import_manifest(*, slug: str | None = None) -> dict:
    slug = slug or f"a24-{uuid.uuid4().hex[:10]}"
    return {
        "name": "Admin Import Fixture",
        "slug": slug,
        "description": "Integration test manifest",
        "source": "integration_test",
        "images": [
            {
                "filename": "img_001.jpg",
                "url": "https://example.com/img_001.jpg",
                "room_type": "living_room",
                "tags": ["living room"],
            },
            {
                "filename": "img_002.jpg",
                "path": "/data/fixtures/img_002.jpg",
                "room_type": "kitchen",
            },
            {
                "filename": "img_003.jpg",
                "storage_path": "s3://bucket/img_003.jpg",
                "room_type": "bedroom",
            },
        ],
    }


@pytest.mark.asyncio
async def test_admin_image_set_import_ok_with_admin_jwt(
    async_client: AsyncClient,
) -> None:
    resp = await async_client.post(
        "/v1/admin/image-sets/import",
        headers={"Authorization": f"Bearer {mint_jwt('admin')}"},
        json=_import_manifest(),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["created_images"] == 3
    assert body["created_items"] == 3
    assert body["reused_images"] == 0
    assert body["skipped_items"] == 0
    assert body["errors"] == []
    assert body["total_in_file"] == 3
    assert isinstance(body["image_set_id"], int)
    assert body["slug"].startswith("a24-")


@pytest.mark.asyncio
async def test_admin_image_set_import_forbidden_for_tagger_jwt(
    async_client: AsyncClient,
) -> None:
    resp = await async_client.post(
        "/v1/admin/image-sets/import",
        headers={"Authorization": f"Bearer {mint_jwt('tagger')}"},
        json=_import_manifest(),
    )
    assert resp.status_code == 403, resp.text
    err = resp.json()["error"]
    assert err["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_admin_image_set_import_forbidden_for_supervisor_jwt(
    async_client: AsyncClient,
) -> None:
    resp = await async_client.post(
        "/v1/admin/image-sets/import",
        headers={"Authorization": f"Bearer {mint_jwt('supervisor')}"},
        json=_import_manifest(),
    )
    assert resp.status_code == 403, resp.text
    err = resp.json()["error"]
    assert err["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_admin_image_set_import_unauthorized_without_bearer(
    async_client: AsyncClient,
) -> None:
    resp = await async_client.post(
        "/v1/admin/image-sets/import",
        json=_import_manifest(),
    )
    assert resp.status_code == 401, resp.text
    err = resp.json()["error"]
    assert err["code"] == "AUTH_REQUIRED"


@pytest.mark.asyncio
async def test_admin_image_set_import_ignores_untrusted_identity_headers(
    async_client: AsyncClient,
) -> None:
    """Client-supplied X-User-* headers must not override JWT role checks."""
    resp = await async_client.post(
        "/v1/admin/image-sets/import",
        headers={
            "Authorization": f"Bearer {mint_jwt('tagger')}",
            "X-User-Id": "00000000-0000-0000-0000-000000000099",
            "X-User-Role": "admin",
        },
        json=_import_manifest(),
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_admin_image_set_import_invalid_manifest_returns_validation_envelope(
    async_client: AsyncClient,
) -> None:
    manifest = _import_manifest()
    manifest["images"] = []
    resp = await async_client.post(
        "/v1/admin/image-sets/import",
        headers={"Authorization": f"Bearer {mint_jwt('admin')}"},
        json=manifest,
    )
    assert resp.status_code == 422, resp.text
    err = resp.json()["error"]
    assert err["code"] == "VALIDATION_ERROR"
    assert err["message"] == "Request validation failed"
    assert isinstance(err["request_id"], str) and err["request_id"]
    assert any(d["field"] == "images" for d in err["details"])
