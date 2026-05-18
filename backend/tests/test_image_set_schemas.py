"""Schema tests for image-set import and browse (Track A, Task A2-2)."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.error_handlers import register_exception_handlers
from backend.schemas.image_sets import (
    ImageSetImportImage,
    ImageSetImportRequest,
    ImageSetImportResponse,
    ImageSetListResponse,
    ImageSetSummary,
)

_SLUG_MAX = 128


def _valid_manifest() -> dict:
    return {
        "name": "COGS 160 Interior Collection",
        "slug": "cogs160-interiors",
        "description": "Interior architecture image collection",
        "source": "local_manifest",
        "images": [
            {
                "filename": "img_001.jpg",
                "url": "https://example.com/img_001.jpg",
                "room_type": "living_room",
                "tags": ["living room"],
            }
        ],
    }


def test_valid_import_request_parses() -> None:
    req = ImageSetImportRequest.model_validate(_valid_manifest())
    assert req.slug == "cogs160-interiors"
    assert len(req.images) == 1
    assert req.images[0].filename == "img_001.jpg"
    assert req.images[0].url == "https://example.com/img_001.jpg"


def test_import_image_accepts_path_or_storage_path() -> None:
    by_path = ImageSetImportImage.model_validate(
        {"filename": "a.jpg", "path": "/data/a.jpg"}
    )
    by_storage = ImageSetImportImage.model_validate(
        {"filename": "b.jpg", "storage_path": "s3://bucket/b.jpg"}
    )
    assert by_path.path == "/data/a.jpg"
    assert by_storage.storage_path == "s3://bucket/b.jpg"


def test_empty_images_list_rejected() -> None:
    payload = _valid_manifest()
    payload["images"] = []
    with pytest.raises(ValidationError) as excinfo:
        ImageSetImportRequest.model_validate(payload)
    assert "images" in str(excinfo.value)


def test_missing_image_location_rejected() -> None:
    with pytest.raises(ValidationError) as excinfo:
        ImageSetImportImage.model_validate({"filename": "img.jpg"})
    assert "url" in str(excinfo.value).lower() or "path" in str(excinfo.value).lower()


def test_empty_filename_rejected() -> None:
    with pytest.raises(ValidationError) as excinfo:
        ImageSetImportImage.model_validate(
            {"filename": "", "url": "https://example.com/x.jpg"}
        )
    assert "filename" in str(excinfo.value)


def test_overlong_slug_rejected() -> None:
    payload = _valid_manifest()
    payload["slug"] = "x" * (_SLUG_MAX + 1)
    with pytest.raises(ValidationError) as excinfo:
        ImageSetImportRequest.model_validate(payload)
    assert "slug" in str(excinfo.value)


def test_import_response_shape() -> None:
    resp = ImageSetImportResponse(
        image_set_id=1,
        slug="demo",
        created_images=2,
        reused_images=1,
        created_items=3,
        skipped_items=0,
        errors=[],
        total_in_file=3,
    )
    data = resp.model_dump()
    assert data["image_set_id"] == 1
    assert data["total_in_file"] == 3
    assert data["errors"] == []


def test_browse_schemas() -> None:
    listing = ImageSetListResponse(
        items=[
            ImageSetSummary(
                id=1,
                slug="demo",
                name="Demo Set",
                item_count=12,
            )
        ]
    )
    assert listing.items[0].item_count == 12


# ─── Validation error envelope (Task A-4) ───────────────────────────────────


@pytest.fixture
def validation_client() -> TestClient:
    app = FastAPI()
    register_exception_handlers(app)

    @app.post("/v1/admin/image-sets/import")
    def _import_image_set(body: ImageSetImportRequest) -> dict[str, str]:
        return {"ok": "true"}

    return TestClient(app, raise_server_exceptions=False)


def test_empty_images_list_returns_validation_envelope(
    validation_client: TestClient,
) -> None:
    payload = _valid_manifest()
    payload["images"] = []
    resp = validation_client.post("/v1/admin/image-sets/import", json=payload)
    assert resp.status_code == 422, resp.text
    err = resp.json()["error"]
    assert err["code"] == "VALIDATION_ERROR"
    assert err["message"] == "Request validation failed"
    assert isinstance(err["request_id"], str) and err["request_id"]
    fields = {d["field"] for d in err["details"]}
    assert "images" in fields


def test_missing_image_location_returns_validation_envelope(
    validation_client: TestClient,
) -> None:
    payload = _valid_manifest()
    payload["images"] = [{"filename": "orphan.jpg"}]
    resp = validation_client.post("/v1/admin/image-sets/import", json=payload)
    assert resp.status_code == 422, resp.text
    err = resp.json()["error"]
    assert err["code"] == "VALIDATION_ERROR"
    assert any("images" in d["field"] for d in err["details"])


def test_empty_filename_returns_validation_envelope(
    validation_client: TestClient,
) -> None:
    payload = _valid_manifest()
    payload["images"] = [{"filename": "", "url": "https://example.com/x.jpg"}]
    resp = validation_client.post("/v1/admin/image-sets/import", json=payload)
    assert resp.status_code == 422, resp.text
    err = resp.json()["error"]
    assert err["code"] == "VALIDATION_ERROR"
    assert any("filename" in d["field"] for d in err["details"])


def test_overlong_slug_returns_validation_envelope(
    validation_client: TestClient,
) -> None:
    payload = _valid_manifest()
    payload["slug"] = "x" * (_SLUG_MAX + 1)
    resp = validation_client.post("/v1/admin/image-sets/import", json=payload)
    assert resp.status_code == 422, resp.text
    err = resp.json()["error"]
    assert err["code"] == "VALIDATION_ERROR"
    assert any(d["field"] == "slug" for d in err["details"])
