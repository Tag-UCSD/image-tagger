"""Smoke-critical Explorer integration tests (Task A-11).

Anonymous public-read: search and detail endpoints must work without
``Authorization`` and must surface shared validation / HTTP error
envelopes per Task A-4.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from backend.tests.conftest import mint_jwt


@pytest.mark.asyncio
async def test_get_explorer_search_ok_without_auth(async_client: AsyncClient) -> None:
    resp = await async_client.get(
        "/v1/explorer/search",
        params={"page": "1", "page_size": "5", "q": ""},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_get_explorer_search_validation_error_envelope(async_client: AsyncClient) -> None:
    resp = await async_client.get("/v1/explorer/search", params={"page": "-5"})
    assert resp.status_code == 422, resp.text
    err = resp.json()["error"]
    assert err["code"] == "VALIDATION_ERROR"
    assert err["message"] == "Request validation failed"
    assert isinstance(err["request_id"], str) and err["request_id"]
    assert isinstance(err["details"], list) and err["details"]
    assert err["details"][0]["field"] == "page"


@pytest.mark.asyncio
async def test_explorer_detail_unknown_image_returns_not_found_envelope(
    async_client: AsyncClient,
) -> None:
    """Detail for a non-existent image returns the contract error envelope."""
    resp = await async_client.get("/v1/explorer/images/999999991/detail")
    assert resp.status_code == 404, resp.text
    err = resp.json()["error"]
    assert err["code"] == "NOT_FOUND"
    assert isinstance(err["request_id"], str) and err["request_id"]


@pytest.mark.asyncio
async def test_explorer_remains_public_with_bogus_auth_header(async_client: AsyncClient) -> None:
    """Explorer search must not start trusting random bearer tokens."""
    resp = await async_client.get(
        "/v1/explorer/search",
        params={"page": "1", "page_size": "1"},
        headers={"Authorization": f"Bearer {mint_jwt('tagger')}"},
    )
    assert resp.status_code == 200, resp.text
