"""Smoke-critical Monitor (supervision) integration tests (Task A-11).

``/v1/monitor/*`` is admin-gated. Monitor endpoints match ``/docs/CONTRACT.md``:
velocity responds with ``series`` (hour buckets) and IRR responds with ``rows``
(both nested lists may be empty on a cold database).
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from backend.tests.conftest import mint_jwt


@pytest.mark.asyncio
async def test_monitor_velocity_requires_admin_role(async_client: AsyncClient) -> None:
    resp = await async_client.get(
        "/v1/monitor/velocity",
        params={"window_hours": "24"},
        headers={"Authorization": f"Bearer {mint_jwt('tagger')}"},
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_monitor_velocity_ok_with_admin_jwt(async_client: AsyncClient) -> None:
    resp = await async_client.get(
        "/v1/monitor/velocity",
        params={"window_hours": "24"},
        headers={"Authorization": f"Bearer {mint_jwt('admin')}"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert isinstance(data.get("series"), list)


@pytest.mark.asyncio
async def test_monitor_irr_returns_empty_list_when_no_overlap(
    async_client: AsyncClient,
) -> None:
    """IRR table starts empty when evidence minimums cannot be satisfied."""
    resp = await async_client.get(
        "/v1/monitor/irr",
        params={"window_hours": "72"},
        headers={"Authorization": f"Bearer {mint_jwt('admin')}"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert isinstance(data.get("rows"), list)
    assert data["rows"] == []
