"""Smoke-critical Workbench integration tests (Task A-11).

Protected routes require a valid bearer JWT; dev-bypass tokens work only
in ``ENVIRONMENT=development`` (local smoke).

Arrange-Act-Assert with ``httpx.AsyncClient`` + ASGI transport from
:mod:`backend.tests.conftest`.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from backend.tests.conftest import mint_jwt


@pytest.mark.asyncio
async def test_workbench_next_with_dev_bypass_tagger(
    async_client: AsyncClient,
    seed_smoke_image_and_attribute: tuple[int, str],
) -> None:
    _image_id, _attr_key = seed_smoke_image_and_attribute
    assert _image_id > 0

    resp = await async_client.get(
        "/v1/workbench/next",
        headers={"Authorization": "Bearer dev_bypass_tagger"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # Shared integration DB may already hold images from earlier tests; queue uses
    # fewest-validations with stable low-id tie-break, not necessarily this fixture's row.
    assert body["id"] > 0
    assert "url" in body and "filename" in body


@pytest.mark.asyncio
async def test_workbench_next_with_minted_tagger_jwt(
    async_client: AsyncClient,
    seed_smoke_image_and_attribute: tuple[int, str],
) -> None:
    _image_id, _key = seed_smoke_image_and_attribute
    resp = await async_client.get(
        "/v1/workbench/next",
        headers={"Authorization": f"Bearer {mint_jwt('tagger')}"},
    )
    assert resp.status_code == 200, resp.text


@pytest.mark.asyncio
async def test_workbench_validate_succeeds_with_dev_bypass(
    async_client: AsyncClient,
    seed_smoke_image_and_attribute: tuple[int, str],
) -> None:
    image_id, attr_key = seed_smoke_image_and_attribute
    payload = {
        "image_id": image_id,
        "attribute_key": attr_key,
        "value": 0.42,
        "duration_ms": 1200,
    }
    resp = await async_client.post(
        "/v1/workbench/validate",
        json=payload,
        headers={"Authorization": "Bearer dev_bypass_tagger"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body.get("status") == "success"
    assert "id" in body


@pytest.mark.asyncio
async def test_workbench_next_unauthorized_returns_auth_envelope(
    async_client: AsyncClient,
) -> None:
    resp = await async_client.get("/v1/workbench/next")
    assert resp.status_code == 401, resp.text
    err = resp.json()["error"]
    assert err["code"] == "AUTH_REQUIRED"
    assert isinstance(err["request_id"], str) and err["request_id"]
