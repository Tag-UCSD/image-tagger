"""Smoke-critical Admin integration tests (Task A-11).

Covers the authentication boundary (401 / 403) and basic happy paths for
budget and asynchronous upload. ``get_total_spent`` is monkeypatched so
the test DB does not need a full :class:`~backend.models.usage.ToolUsage`
ledger.
"""

from __future__ import annotations

import io

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
