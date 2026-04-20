"""Tests for science_runs service layer and canonical API endpoints.

Uses FastAPI's TestClient with an in-memory SQLite DB so no running
Postgres is required. The TestClient exercises:
  - science/bootstrap  POST
  - science/status     GET
  - image detail       GET (canonical outputs block)
"""
import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def _admin_headers():
    return {
        "X-User-Id": "1",
        "X-User-Role": "admin",
        "X-Auth-Token": "dev_secret_key_change_me",
    }


def _tagger_headers():
    return {
        "X-User-Id": "1",
        "X-User-Role": "tagger",
    }


# ── ScienceRunContext ─────────────────────────────────────────────────────────

class TestScienceRunContext:
    def test_add_tag_appends(self):
        from backend.science.run_context import ScienceRunContext
        ctx = ScienceRunContext(image_id=1, science_version="v", config_fingerprint="fp")
        ctx.add_tag(tag_key="room_type.kitchen", label="Kitchen", namespace="room_type", confidence=0.7)
        assert len(ctx.tags) == 1
        assert ctx.tags[0].label == "Kitchen"

    def test_tag_keys_returns_set(self):
        from backend.science.run_context import ScienceRunContext
        ctx = ScienceRunContext(image_id=1, science_version="v", config_fingerprint="fp")
        ctx.add_tag("a.b", "B", "a")
        ctx.add_tag("c.d", "D", "c")
        assert ctx.tag_keys() == {"a.b", "c.d"}

    def test_add_artifact_appends(self):
        from backend.science.run_context import ScienceRunContext
        ctx = ScienceRunContext(image_id=1, science_version="v", config_fingerprint="fp")
        ctx.add_artifact("room_json", meta_json={"top_coarse": ["bedroom", 0.9]})
        assert len(ctx.artifacts) == 1
        assert ctx.artifacts[0].artifact_type == "room_json"

    def test_as_dict_roundtrip(self):
        from backend.science.run_context import ScienceTagRecord
        rec = ScienceTagRecord(
            tag_key="room_type.lobby",
            label="Lobby",
            namespace="room_type",
            confidence=0.634,
            source_analyzer="places365",
            attribute_key="room.type_coarse",
        )
        d = rec.as_dict()
        assert d["tag_key"] == "room_type.lobby"
        assert d["confidence"] == 0.634
        assert set(d.keys()) == {
            "tag_key", "label", "namespace", "confidence",
            "source_analyzer", "attribute_key",
        }


# ── Bootstrap endpoint ────────────────────────────────────────────────────────

class TestBootstrapEndpoint:
    def test_bootstrap_returns_200(self):
        resp = client.post("/v1/explorer/science/bootstrap", headers=_admin_headers())
        assert resp.status_code == 200, resp.text

    def test_bootstrap_response_shape(self):
        resp = client.post("/v1/explorer/science/bootstrap", headers=_admin_headers())
        data = resp.json()
        for field in ("science_version", "queued", "already_current", "running", "failed", "total_images"):
            assert field in data, f"Missing field: {field}"

    def test_bootstrap_counts_are_non_negative(self):
        resp = client.post("/v1/explorer/science/bootstrap", headers=_admin_headers())
        data = resp.json()
        for key in ("queued", "already_current", "running", "failed", "total_images"):
            assert data[key] >= 0, f"{key} is negative: {data[key]}"


# ── Status endpoint ───────────────────────────────────────────────────────────

class TestStatusEndpoint:
    def test_status_returns_200(self):
        resp = client.get("/v1/explorer/science/status", headers=_admin_headers())
        assert resp.status_code == 200, resp.text

    def test_status_response_shape(self):
        resp = client.get("/v1/explorer/science/status", headers=_admin_headers())
        data = resp.json()
        for field in ("science_version", "config_fingerprint", "current_completed",
                      "pending", "running", "failed", "total_images"):
            assert field in data, f"Missing field: {field}"

    def test_status_science_version_matches_active(self):
        from backend.services.science_runs import ACTIVE_SCIENCE_VERSION
        resp = client.get("/v1/explorer/science/status", headers=_admin_headers())
        assert resp.json()["science_version"] == ACTIVE_SCIENCE_VERSION


# ── Image detail — canonical outputs block ────────────────────────────────────

def _first_image_id() -> int | None:
    """Return the first image ID from search, or None if empty."""
    resp = client.post(
        "/v1/explorer/search",
        json={"query_string": "", "page": 1, "page_size": 1},
        headers=_tagger_headers(),
    )
    if resp.status_code != 200:
        return None
    items = resp.json()  # search returns a plain list
    return items[0]["id"] if items else None


class TestImageDetailCanonicalOutputs:
    def test_detail_404_for_nonexistent_image(self):
        resp = client.get("/v1/explorer/images/999999/detail", headers=_tagger_headers())
        assert resp.status_code == 404

    def test_detail_includes_science_run_field(self):
        image_id = _first_image_id()
        if image_id is None:
            pytest.skip("No images in test database")

        resp = client.get(f"/v1/explorer/images/{image_id}/detail", headers=_tagger_headers())
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "science_run" in data
        assert "canonical_outputs_available" in data

    def test_detail_canonical_outputs_available_is_bool(self):
        image_id = _first_image_id()
        if image_id is None:
            pytest.skip("No images in test database")

        resp = client.get(f"/v1/explorer/images/{image_id}/detail", headers=_tagger_headers())
        data = resp.json()
        assert isinstance(data["canonical_outputs_available"], bool)

    def test_detail_tags_list_present(self):
        image_id = _first_image_id()
        if image_id is None:
            pytest.skip("No images in test database")

        resp = client.get(f"/v1/explorer/images/{image_id}/detail", headers=_tagger_headers())
        data = resp.json()
        assert isinstance(data["tags"], list)

    def test_science_run_shape_when_present(self):
        """If science_run is not null it must have the expected fields."""
        image_id = _first_image_id()
        if image_id is None:
            pytest.skip("No images in test database")

        resp = client.get(f"/v1/explorer/images/{image_id}/detail", headers=_tagger_headers())
        data = resp.json()
        run = data.get("science_run")
        if run is None:
            pytest.skip("No science run for this image yet")

        for field in ("status", "science_version", "config_fingerprint"):
            assert field in run, f"science_run missing field: {field}"
        assert run["status"] in ("PENDING", "RUNNING", "COMPLETED", "FAILED", "STALE")


# ── Search — science_run_status field ────────────────────────────────────────

class TestSearchCanonicalStatus:
    def test_search_results_include_science_run_status_field(self):
        resp = client.post(
            "/v1/explorer/search",
            json={"query_string": "", "page": 1, "page_size": 5},
            headers=_tagger_headers(),
        )
        assert resp.status_code == 200, resp.text
        items = resp.json()  # search returns a plain list
        for item in items:
            assert "science_run_status" in item
            # May be null (no run queued) or one of the known statuses
            status = item["science_run_status"]
            if status is not None:
                assert status in ("PENDING", "RUNNING", "COMPLETED", "FAILED", "STALE")
