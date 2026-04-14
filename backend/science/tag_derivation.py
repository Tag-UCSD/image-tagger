"""
Canonical tag derivation rules.

Derives ScienceTagRecords from science run outputs (attributes, structured
summaries). Centralises thresholds so the API layer never invents new
canonical tags at read time.

All functions mutate the passed ScienceRunContext by appending tag records.
"""
from __future__ import annotations

import logging
from typing import Any

from backend.science.run_context import ScienceRunContext

logger = logging.getLogger("v3.science.tag_derivation")

# ── Affordance thresholds ─────────────────────────────────────────────────────
# Scores are on a 1-7 Likert scale from LightGBM regressors.
AFFORDANCE_LABELS = {
    "L059": "Sleep",
    "L079": "Cook",
    "L091": "Work",
    "L130": "Converse",
    "L141": "Yoga",
}
AFFORDANCE_HIGH_THRESHOLD = 5.5   # ≥ 5.5 → "high"
AFFORDANCE_MED_THRESHOLD  = 3.5   # ≥ 3.5 → "medium"; below → no tag

# ── Room type thresholds ──────────────────────────────────────────────────────
ROOM_CONFIDENCE_THRESHOLD = 0.20  # Coarse room confidence ≥ 20% → emit tag

# ── Object thresholds ─────────────────────────────────────────────────────────
OBJECT_COVERAGE_THRESHOLD   = 0.01  # Object must cover ≥ 1% of frame
OBJECT_CONFIDENCE_THRESHOLD = 0.30  # Detection confidence ≥ 30%

# ── Science attribute namespaces promoted to tags ─────────────────────────────
SCIENCE_TAG_NAMESPACES = ("style.", "cognitive.", "biophilia.")
SCIENCE_TAG_THRESHOLD  = 0.5  # Attribute value ≥ 0.5 → emit tag
MATERIAL_TAG_THRESHOLD = 0.04  # Estimated scene share ≥ 4% → emit tag


def derive_affordance_tags(
    affordance_summary: dict,
    ctx: ScienceRunContext,
) -> None:
    """Emit canonical affordance tags from affordance score summary."""
    scores = affordance_summary.get("scores", {})
    for aff_id, score in scores.items():
        label_base = AFFORDANCE_LABELS.get(aff_id, aff_id)
        try:
            score_f = float(score)
        except (TypeError, ValueError):
            continue

        if score_f >= AFFORDANCE_HIGH_THRESHOLD:
            level = "high"
        elif score_f >= AFFORDANCE_MED_THRESHOLD:
            level = "medium"
        else:
            continue  # Low affordance — not worth a canonical tag

        aff_id_lower = aff_id.lower()
        tag_key = f"affordance.{aff_id_lower}.{level}"
        ctx.add_tag(
            tag_key=tag_key,
            label=f"{label_base} ({level})",
            namespace="affordance",
            confidence=round((score_f - 1.0) / 6.0, 3),
            source_analyzer="affordance_lgbm",
            attribute_key=f"affordance.{aff_id}",
        )


def derive_room_tags(
    room_summary: dict,
    ctx: ScienceRunContext,
) -> None:
    """Emit the primary canonical room-type tag from room detection results."""
    top_coarse = room_summary.get("top_coarse")
    if not top_coarse:
        return

    room_label, confidence = top_coarse
    if not room_label or float(confidence) < ROOM_CONFIDENCE_THRESHOLD:
        return

    tag_key = f"room_type.{room_label}"
    display = " ".join(w.capitalize() for w in room_label.replace("_", " ").split())
    ctx.add_tag(
        tag_key=tag_key,
        label=display,
        namespace="room_type",
        confidence=round(float(confidence), 3),
        source_analyzer="places365",
        attribute_key="room.type_coarse",
    )


def derive_object_tags(
    segmentation_summary: dict,
    ctx: ScienceRunContext,
) -> None:
    """Emit canonical object tags from segmentation object summary."""
    objects = segmentation_summary.get("objects", [])
    for obj in objects:
        class_name = obj.get("class_name", "")
        coverage = float(obj.get("coverage_ratio", 0.0))
        confidence = float(obj.get("confidence", 0.0))
        if coverage < OBJECT_COVERAGE_THRESHOLD:
            continue
        if confidence < OBJECT_CONFIDENCE_THRESHOLD:
            continue
        safe = class_name.replace(" ", "_").lower()
        tag_key = f"object.{safe}"
        display = " ".join(w.capitalize() for w in class_name.split())
        ctx.add_tag(
            tag_key=tag_key,
            label=display,
            namespace="object",
            confidence=round(confidence, 3),
            source_analyzer="segmentation",
        )


def derive_science_attribute_tags(
    attributes: dict[str, float],
    ctx: ScienceRunContext,
) -> None:
    """Promote high-confidence semantic science attributes to canonical tags.

    Only style.* and cognitive.* namespaces are promoted; numeric physics
    attributes (color, texture, etc.) are not tagged.
    """
    for key, value in attributes.items():
        if not any(key.startswith(ns) for ns in SCIENCE_TAG_NAMESPACES):
            continue
        try:
            value_f = float(value)
        except (TypeError, ValueError):
            continue
        if value_f < SCIENCE_TAG_THRESHOLD:
            continue
        last = key.rsplit(".", 1)[-1]
        label = " ".join(w.capitalize() for w in last.split("_"))
        ns = key.split(".")[0]
        ctx.add_tag(
            tag_key=key,
            label=label,
            namespace=ns,
            confidence=round(value_f, 3),
            source_analyzer="science_pipeline",
            attribute_key=key,
        )


def derive_material_tags(
    materials_summary: dict,
    ctx: ScienceRunContext,
) -> None:
    """Emit canonical material tags with visible coverage percentages."""
    materials = (
        materials_summary.get("materials_aggregated")
        or materials_summary.get("materials")
        or []
    )
    for material in materials:
        name = str(material.get("material", "")).strip().lower()
        if not name:
            continue
        share = float(material.get("coverage_3d", material.get("coverage_2d", 0.0)))
        if share < MATERIAL_TAG_THRESHOLD:
            continue
        label = f"{' '.join(w.capitalize() for w in name.split('_'))} {round(share * 100):.0f}%"
        ctx.add_tag(
            tag_key=f"material.{name}",
            label=label,
            namespace="material",
            confidence=round(float(material.get("confidence", share)), 3),
            source_analyzer=str(materials_summary.get("engine", "materials")),
            attribute_key=f"material.vlm.{name}_coverage_3d",
        )


def derive_all_tags(
    attributes: dict[str, float],
    affordance_summary: dict | None,
    room_summary: dict | None,
    segmentation_summary: dict | None,
    materials_summary: dict | None,
    ctx: ScienceRunContext,
) -> None:
    """Run all tag derivation rules and accumulate results into ctx."""
    if affordance_summary:
        derive_affordance_tags(affordance_summary, ctx)
    if room_summary:
        derive_room_tags(room_summary, ctx)
    if segmentation_summary:
        derive_object_tags(segmentation_summary, ctx)
    if materials_summary:
        derive_material_tags(materials_summary, ctx)
    derive_science_attribute_tags(attributes, ctx)
