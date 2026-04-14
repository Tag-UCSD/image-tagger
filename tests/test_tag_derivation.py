"""Unit tests for canonical tag derivation rules (science/tag_derivation.py).

All tests are pure in-memory — no database required.
"""
import pytest

from backend.science.run_context import ScienceRunContext
from backend.science.tag_derivation import (
    AFFORDANCE_HIGH_THRESHOLD,
    AFFORDANCE_MED_THRESHOLD,
    ROOM_CONFIDENCE_THRESHOLD,
    SCIENCE_TAG_THRESHOLD,
    derive_affordance_tags,
    derive_all_tags,
    derive_material_tags,
    derive_object_tags,
    derive_room_tags,
    derive_science_attribute_tags,
)


def _ctx() -> ScienceRunContext:
    return ScienceRunContext(
        image_id=1,
        science_version="test",
        config_fingerprint="abc123",
    )


# ── Affordance ────────────────────────────────────────────────────────────────

class TestDeriveAffordanceTags:
    def test_high_affordance_emits_high_tag(self):
        ctx = _ctx()
        derive_affordance_tags({"scores": {"L059": AFFORDANCE_HIGH_THRESHOLD}}, ctx)
        assert any(t.tag_key == "affordance.l059.high" for t in ctx.tags)

    def test_medium_affordance_emits_medium_tag(self):
        ctx = _ctx()
        derive_affordance_tags({"scores": {"L079": AFFORDANCE_MED_THRESHOLD}}, ctx)
        assert any(t.tag_key == "affordance.l079.medium" for t in ctx.tags)

    def test_low_affordance_no_tag(self):
        ctx = _ctx()
        derive_affordance_tags({"scores": {"L091": AFFORDANCE_MED_THRESHOLD - 0.1}}, ctx)
        assert not ctx.tags

    def test_confidence_is_normalised_to_0_1(self):
        ctx = _ctx()
        derive_affordance_tags({"scores": {"L059": 7.0}}, ctx)
        tag = ctx.tags[0]
        assert 0.0 <= tag.confidence <= 1.0

    def test_unknown_aff_id_still_emits(self):
        ctx = _ctx()
        derive_affordance_tags({"scores": {"L999": 6.0}}, ctx)
        assert ctx.tags

    def test_empty_scores_no_tags(self):
        ctx = _ctx()
        derive_affordance_tags({"scores": {}}, ctx)
        assert not ctx.tags

    def test_namespace_is_affordance(self):
        ctx = _ctx()
        derive_affordance_tags({"scores": {"L059": 6.0}}, ctx)
        assert ctx.tags[0].namespace == "affordance"


# ── Room type ─────────────────────────────────────────────────────────────────

class TestDeriveRoomTags:
    def test_confident_room_emits_tag(self):
        ctx = _ctx()
        derive_room_tags({"top_coarse": ["bedroom", 0.65]}, ctx)
        assert any(t.tag_key == "room_type.bedroom" for t in ctx.tags)

    def test_low_confidence_no_tag(self):
        ctx = _ctx()
        derive_room_tags({"top_coarse": ["bedroom", ROOM_CONFIDENCE_THRESHOLD - 0.01]}, ctx)
        assert not ctx.tags

    def test_exact_threshold_emits_tag(self):
        ctx = _ctx()
        derive_room_tags({"top_coarse": ["kitchen", ROOM_CONFIDENCE_THRESHOLD]}, ctx)
        assert ctx.tags

    def test_label_is_capitalised(self):
        ctx = _ctx()
        derive_room_tags({"top_coarse": ["living_room", 0.50]}, ctx)
        assert ctx.tags[0].label == "Living Room"

    def test_attribute_key_is_room_type_coarse(self):
        ctx = _ctx()
        derive_room_tags({"top_coarse": ["lobby", 0.80]}, ctx)
        assert ctx.tags[0].attribute_key == "room.type_coarse"

    def test_namespace_is_room_type(self):
        ctx = _ctx()
        derive_room_tags({"top_coarse": ["lobby", 0.80]}, ctx)
        assert ctx.tags[0].namespace == "room_type"

    def test_missing_top_coarse_no_tag(self):
        ctx = _ctx()
        derive_room_tags({}, ctx)
        assert not ctx.tags

    def test_none_room_label_no_tag(self):
        ctx = _ctx()
        derive_room_tags({"top_coarse": [None, 0.9]}, ctx)
        assert not ctx.tags


# ── Objects ───────────────────────────────────────────────────────────────────

class TestDeriveObjectTags:
    def _seg(self, class_name="chair", coverage=0.05, confidence=0.80):
        return {"objects": [{"class_name": class_name, "coverage_ratio": coverage, "confidence": confidence}]}

    def test_valid_object_emits_tag(self):
        ctx = _ctx()
        derive_object_tags(self._seg(), ctx)
        assert any(t.tag_key == "object.chair" for t in ctx.tags)

    def test_low_coverage_no_tag(self):
        ctx = _ctx()
        derive_object_tags(self._seg(coverage=0.005), ctx)
        assert not ctx.tags

    def test_low_confidence_no_tag(self):
        ctx = _ctx()
        derive_object_tags(self._seg(confidence=0.25), ctx)
        assert not ctx.tags

    def test_spaces_replaced_with_underscores(self):
        ctx = _ctx()
        derive_object_tags(self._seg(class_name="dining table"), ctx)
        assert any("dining_table" in t.tag_key for t in ctx.tags)

    def test_empty_objects_no_tags(self):
        ctx = _ctx()
        derive_object_tags({"objects": []}, ctx)
        assert not ctx.tags


# ── Science attribute tags ────────────────────────────────────────────────────

class TestDeriveScienceAttributeTags:
    def test_style_attribute_above_threshold_emits_tag(self):
        ctx = _ctx()
        derive_science_attribute_tags({"style.minimalist": SCIENCE_TAG_THRESHOLD}, ctx)
        assert any(t.namespace == "style" for t in ctx.tags)

    def test_cognitive_attribute_above_threshold_emits_tag(self):
        ctx = _ctx()
        derive_science_attribute_tags({"cognitive.restorative": 0.8}, ctx)
        assert any(t.namespace == "cognitive" for t in ctx.tags)

    def test_biophilia_attribute_above_threshold_emits_tag(self):
        ctx = _ctx()
        derive_science_attribute_tags({"biophilia.index": SCIENCE_TAG_THRESHOLD}, ctx)
        assert any(t.namespace == "biophilia" for t in ctx.tags)

    def test_color_attribute_not_promoted(self):
        ctx = _ctx()
        derive_science_attribute_tags({"color.saturation_mean": 0.9}, ctx)
        assert not ctx.tags

    def test_below_threshold_no_tag(self):
        ctx = _ctx()
        derive_science_attribute_tags({"style.minimalist": SCIENCE_TAG_THRESHOLD - 0.01}, ctx)
        assert not ctx.tags


class TestDeriveMaterialTags:
    def test_material_with_share_emits_tag(self):
        ctx = _ctx()
        derive_material_tags(
            {
                "materials": [
                    {"material": "wood", "coverage_3d": 0.21, "confidence": 0.91},
                ]
            },
            ctx,
        )
        assert any(t.tag_key == "material.wood" for t in ctx.tags)
        assert any("21%" in t.label for t in ctx.tags)


# ── derive_all_tags ───────────────────────────────────────────────────────────

class TestDeriveAllTags:
    def test_none_summaries_skips_them(self):
        ctx = _ctx()
        derive_all_tags(
            attributes={"style.modern": 0.9},
            affordance_summary=None,
            room_summary=None,
            segmentation_summary=None,
            materials_summary=None,
            ctx=ctx,
        )
        assert ctx.tags
        assert all(t.namespace == "style" for t in ctx.tags)

    def test_all_summaries_combined(self):
        ctx = _ctx()
        derive_all_tags(
            attributes={"style.cozy": 0.8},
            affordance_summary={"scores": {"L059": 6.0}},
            room_summary={"top_coarse": ["bedroom", 0.70]},
            segmentation_summary=None,
            materials_summary={"materials": [{"material": "wood", "coverage_3d": 0.18, "confidence": 0.9}]},
            ctx=ctx,
        )
        namespaces = {t.namespace for t in ctx.tags}
        assert "room_type" in namespaces
        assert "affordance" in namespaces
        assert "style" in namespaces
        assert "material" in namespaces

    def test_tag_keys_are_unique_by_default(self):
        ctx = _ctx()
        derive_all_tags(
            attributes={"style.modern": 0.9},
            affordance_summary={"scores": {"L059": 6.0}},
            room_summary={"top_coarse": ["bedroom", 0.70]},
            segmentation_summary=None,
            materials_summary={"materials": [{"material": "wood", "coverage_3d": 0.18, "confidence": 0.9}]},
            ctx=ctx,
        )
        keys = [t.tag_key for t in ctx.tags]
        assert len(keys) == len(set(keys)), "Duplicate tag keys found"
