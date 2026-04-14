"""
Explorer / Discovery API (v1).

This module is the canonical adaptor between the Explorer UI and the
database + training export service. It exposes three main endpoints:

- POST /v1/explorer/search
- POST /v1/explorer/export
- GET  /v1/explorer/attributes

All endpoints are RBAC-protected for taggers (and above).
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
import os
import threading
from typing import List, Optional
from pathlib import Path

import cv2
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
import numpy as np
import requests
from sqlalchemy.orm import Session

from backend.database.core import get_db, SessionLocal
from backend.services.auth import require_tagger
from backend.services.training_export import TrainingExporter
from backend.schemas.training import TrainingExample
from backend.schemas.discovery import (
    SearchQuery, ImageSearchResult, ExportRequest, AttributeRead,
    AttributeValue, HumanValidation, ImageDetailResult, TagInfo, AffordanceScore,
    ScienceRunInfo, BootstrapResponse, ScienceStatusResponse,
)
from backend.models.attribute import Attribute
from backend.models.assets import Image
from backend.science.context.affordance import (
    AFFORDANCE_IDS,
    AFFORDANCE_NAMES,
    predict_affordances_with_metadata_from_image,
)

logger = logging.getLogger("v3.api.discovery")

router = APIRouter(prefix="/v1/explorer", tags=["explorer"])


_AFFORDANCE_CACHE_KEY = "affordance_runtime_v1"


def _is_url(path: str) -> bool:
    return path.startswith("http://") or path.startswith("https://")


def _resolve_path(storage_path: str) -> Path:
    raw = Path(storage_path)
    if raw.is_file():
        return raw
    root = Path("data_store")
    candidate = root / storage_path
    if candidate.is_file():
        return candidate
    env_root_value = os.getenv("IMAGE_STORAGE_ROOT", "")
    if env_root_value:
        env_root = Path(env_root_value)
        env_candidate = env_root / storage_path
        if env_candidate.is_file():
            return env_candidate
    return raw


def _load_image_rgb(storage_path: str) -> np.ndarray:
    if _is_url(storage_path):
        resp = requests.get(storage_path, timeout=15)
        resp.raise_for_status()
        arr = np.frombuffer(resp.content, dtype=np.uint8)
        bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    else:
        path = _resolve_path(storage_path)
        if not path.is_file():
            raise FileNotFoundError(f"Image file not found: {path}")
        bgr = cv2.imread(str(path))
    if bgr is None:
        raise ValueError(f"Could not load image: {storage_path}")
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)


def _score_list_from_map(score_map: dict | None) -> list[AffordanceScore]:
    score_map = score_map or {}
    out: list[AffordanceScore] = []
    for aff_id in AFFORDANCE_IDS:
        if aff_id not in score_map:
            continue
        out.append(AffordanceScore(
            id=aff_id,
            label=AFFORDANCE_NAMES.get(aff_id, aff_id),
            score=float(score_map[aff_id]),
        ))
    return out


def _get_cached_affordance_payload(image: Image) -> dict | None:
    meta = getattr(image, "meta_data", {}) or {}
    payload = meta.get(_AFFORDANCE_CACHE_KEY)
    if isinstance(payload, dict) and isinstance(payload.get("scores"), dict):
        scores = payload.get("scores") or {}
        if any((not isinstance(v, (int, float))) or float(v) < 1.0 or float(v) > 7.0 for v in scores.values()):
            return None
        return payload
    return None


def _compute_and_cache_affordance_payload(image: Image, db: Session) -> dict:
    try:
        rgb = _load_image_rgb(image.storage_path)
        predicted = predict_affordances_with_metadata_from_image(rgb)
        payload = {
            "scores": {k: round(float(v), 3) for k, v in predicted.get("scores", {}).items()},
            "method": predicted.get("method"),
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception:
        payload = {
            "scores": {},
            "method": "unavailable",
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }
    meta = dict(getattr(image, "meta_data", {}) or {})
    meta[_AFFORDANCE_CACHE_KEY] = payload
    image.meta_data = meta
    db.add(image)
    db.commit()
    db.refresh(image)
    return payload


def _get_or_compute_affordance_payload(image: Image, db: Session) -> dict:
    cached = _get_cached_affordance_payload(image)
    if cached is not None:
        return cached
    return _compute_and_cache_affordance_payload(image, db)


@router.post("/search", response_model=List[ImageSearchResult])
def search_images(
    payload: SearchQuery,
    db: Session = Depends(get_db),
    user=Depends(require_tagger),
) -> List[ImageSearchResult]:
    """Search for images matching the query.

    This minimal implementation supports:
      - free-text search over image name / description (if available), or
      - returning a simple paginated list when no filter is provided.

    The exact ranking can be improved later; for now we favour determinism
    and well-formed responses over sophistication.
    """
    # Lazy import to avoid circular dependencies
    from backend.models.assets import Image  # type: ignore

    q = db.query(Image)

    if getattr(payload, "text", None):
        text = f"%{payload.text}%"
        # Try to filter by name / description if those fields exist.
        # We guard each attribute access with hasattr to avoid hard failures
        # across slightly different schemas.
        name_col = getattr(Image, "name", None)
        desc_col = getattr(Image, "description", None)
        if name_col is not None and desc_col is not None:
            q = q.filter((name_col.ilike(text)) | (desc_col.ilike(text)))
        elif name_col is not None:
            q = q.filter(name_col.ilike(text))

    # Use page/page_size from schema (frontend sends these)
    page = max(1, getattr(payload, "page", 1))
    page_size = max(1, min(getattr(payload, "page_size", 48), 200))
    offset = (page - 1) * page_size
    q = q.order_by(getattr(Image, "id")).offset(offset).limit(page_size)

    images = q.all()
    if not images:
        return []

    # ── Batch-load canonical science run state and tags ───────────────────────
    # Single IN query per result set — avoids N+1 per image.
    from backend.models.science_runs import ScienceRun, ScienceTag
    from backend.services.science_runs import (
        get_active_science_version,
        get_config_fingerprint,
    )

    image_ids = [img.id for img in images if img.id is not None]
    version = get_active_science_version()
    fingerprint = get_config_fingerprint()

    runs = (
        db.query(ScienceRun)
        .filter(
            ScienceRun.image_id.in_(image_ids),
            ScienceRun.science_version == version,
            ScienceRun.config_fingerprint == fingerprint,
        )
        .all()
    )
    run_status_map = {r.image_id: r.status for r in runs}
    completed_run_ids = [r.id for r in runs if r.status == "COMPLETED"]

    # Canonical tags keyed by image_id (labels only for grid display)
    canonical_tags_map: dict[int, list[str]] = {}
    if completed_run_ids:
        canon_tags = (
            db.query(ScienceTag.image_id, ScienceTag.label)
            .filter(
                ScienceTag.science_run_id.in_(completed_run_ids),
                ScienceTag.is_canonical.is_(True),
            )
            .all()
        )
        for img_id, label in canon_tags:
            canonical_tags_map.setdefault(img_id, []).append(label)

    # ── Build results ─────────────────────────────────────────────────────────
    results: List[ImageSearchResult] = []
    base_thumb_url = "/static/thumbnails"

    for img in images:
        image_id = getattr(img, "id", None)
        if image_id is None:
            continue

        storage_path = getattr(img, "storage_path", None)
        if storage_path and storage_path.startswith("http"):
            url = storage_path
        else:
            thumb_name = getattr(img, "thumbnail_path", None) or f"image_{image_id}.jpg"
            url = f"{base_thumb_url}/{thumb_name}"

        meta = getattr(img, "meta_data", {}) or {}
        imported_tags: list[str] = meta.get("tags", []) if isinstance(meta, dict) else []

        # Merge imported tags with canonical pipeline tags (deduped, imported first)
        pipeline_tags = canonical_tags_map.get(image_id, [])
        imported_lower = {t.lower() for t in imported_tags}
        merged_tags = list(imported_tags) + [
            t for t in pipeline_tags if t.lower() not in imported_lower
        ]

        affordance_payload = _get_cached_affordance_payload(img)
        results.append(ImageSearchResult(
            id=image_id,
            url=url,
            tags=merged_tags,
            meta_data=meta,
            affordance_scores=_score_list_from_map((affordance_payload or {}).get("scores")),
            affordance_method=(affordance_payload or {}).get("method"),
            science_run_status=run_status_map.get(image_id),
        ))

    return results


@router.post("/export", response_model=List[TrainingExample])
def export_training_data(
    payload: ExportRequest,
    db: Session = Depends(get_db),
    user=Depends(require_tagger),
) -> List[TrainingExample]:
    """Export training examples for the given image IDs.

    This is a thin wrapper around the TrainingExporter service, returning
    a list of TrainingExample objects suitable for downstream model training.
    """
    if not payload.image_ids:
        return []

    exporter = TrainingExporter(db=db)
    try:
        examples = exporter.export_for_images(payload.image_ids)
    except Exception as exc:  # pragma: no cover - defensive logging
        raise HTTPException(status_code=500, detail=f"training export failed: {exc}") from exc

    return examples


@router.get("/attributes", response_model=List[AttributeRead])
def list_attributes(
    db: Session = Depends(get_db),
    user=Depends(require_tagger),
) -> List[AttributeRead]:
    """Return the attribute registry for Explorer filters.

    We expose all Attribute rows, mapping them into AttributeRead records.
    Pydantic's from_attributes=True handles the ORM-to-schema conversion.
    """
    attrs = db.query(Attribute).order_by(Attribute.key).all()
    return [AttributeRead.model_validate(attr) for attr in attrs]


@router.get("/images/{image_id}/detail", response_model=ImageDetailResult)
def get_image_detail(
    image_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_tagger),
) -> ImageDetailResult:
    """Return the full detail payload for the single-image viewer modal.

    Fetches the image record, all Validation rows for that image, and the
    Attribute registry in a single pass. Returns science-pipeline attributes
    and human validations as separate lists, ready for the frontend to render.
    """
    from backend.models.annotation import Validation  # avoid circular import
    from backend.models.users import User

    image = db.query(Image).filter(Image.id == image_id).first()
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found")

    # Build URL (same logic as search_images)
    storage_path = getattr(image, "storage_path", None)
    if storage_path and storage_path.startswith("http"):
        url = storage_path
    else:
        thumb_name = getattr(image, "thumbnail_path", None) or f"image_{image_id}.jpg"
        url = f"/static/thumbnails/{thumb_name}"

    # Fetch all validations for this image
    validations = (
        db.query(Validation)
        .filter(Validation.image_id == image_id)
        .order_by(Validation.attribute_key)
        .all()
    )

    # Load attribute registry for name/category lookup
    attr_registry = {a.key: a for a in db.query(Attribute).all()}

    # Load user map for username lookup (single query for all users needed)
    user_ids = {v.user_id for v in validations if v.user_id is not None}
    if user_ids:
        users = db.query(User).filter(User.id.in_(user_ids)).all()
        user_map = {u.id: u.username for u in users}
    else:
        user_map = {}

    science_attributes: list[AttributeValue] = []
    human_validations: list[HumanValidation] = []

    for v in validations:
        attr = attr_registry.get(v.attribute_key)
        is_science = bool(v.source and v.source.startswith("science_pipeline"))

        if is_science:
            science_attributes.append(AttributeValue(
                key=v.attribute_key,
                name=attr.name if attr else v.attribute_key,
                category=attr.category if attr else None,
                value=float(v.value),
                source=v.source,
            ))
        else:
            human_validations.append(HumanValidation(
                user_id=v.user_id,
                username=user_map.get(v.user_id) if v.user_id else None,
                attribute_key=v.attribute_key,
                value=float(v.value),
                duration_ms=v.duration_ms if v.duration_ms else None,
                created_at=v.created_at,
            ))

    meta = getattr(image, "meta_data", {}) or {}
    affordance_payload = _get_cached_affordance_payload(image) or {}
    raw_tags = meta.get("tags", []) if isinstance(meta, dict) else []
    filename = getattr(image, "filename", None) or meta.get("filename", f"image_{image_id}")

    # ── Build tag provenance ──────────────────────────────────────────────────
    # Map attribute key namespace prefix → human-readable analyzer name.
    _NAMESPACE_SOURCE: dict[str, str] = {
        "style":       "Semantic Tagger · VLM",
        "cognitive":   "Cognitive Analyzer · VLM",
        "color":       "Color Analyzer · CIELAB",
        "texture":     "Texture Analyzer · GLCM",
        "fractal":     "Fractal Dimension Analyzer",
        "symmetry":    "Symmetry Analyzer",
        "naturalness": "Naturalness Analyzer",
        "fluency":     "Fluency Analyzer",
        "spatial":     "Depth / Spatial Analyzer",
        "material":    "Material Analyzer",
        "materials":   "Material Analyzer",
        "segmentation":"Segmentation · OneFormer",
        "science":     "Complexity Analyzer · Canny",
    }

    def _key_to_label(key: str) -> str:
        """'style.minimalist' → 'Minimalist',  'spatial.room_function.home_office' → 'Home Office'"""
        last = key.rsplit(".", 1)[-1]
        return " ".join(w.capitalize() for w in last.split("_"))

    def _source_label_for(key: str) -> str:
        if "room_function" in key:
            return "Room Classifier · VLM"
        ns = key.split(".")[0]
        return _NAMESPACE_SOURCE.get(ns, "Science Pipeline")

    # ── Load canonical science run state ─────────────────────────────────────
    from backend.services.science_runs import (
        get_current_run_for_image,
        get_science_tags_for_run,
    )

    current_run = get_current_run_for_image(db, image_id)
    run_info: ScienceRunInfo | None = None
    canonical_tags: list[TagInfo] = []
    canonical_outputs_available = False

    if current_run is not None:
        run_info = ScienceRunInfo(
            status=current_run.status,
            science_version=current_run.science_version,
            config_fingerprint=current_run.config_fingerprint,
            queued_at=current_run.queued_at,
            started_at=current_run.started_at,
            completed_at=current_run.completed_at,
            error_message=current_run.error_message,
            trigger_source=current_run.trigger_source,
        )

        if current_run.status == "COMPLETED":
            canonical_outputs_available = True
            science_tags = get_science_tags_for_run(db, current_run.id, image_id)
            canonical_tags = [
                TagInfo(
                    label=st.label,
                    source="science_pipeline",
                    source_label=_source_label_for(st.attribute_key or st.tag_key),
                    confidence=st.confidence,
                    attribute_key=st.attribute_key or st.tag_key,
                )
                for st in science_tags
            ]

    # ── Build tag list: preloaded first, then canonical (preferred) or legacy ─
    tag_infos: list[TagInfo] = [
        TagInfo(label=t, source="preloaded", source_label="Imported with dataset")
        for t in raw_tags
    ]

    if canonical_outputs_available and canonical_tags:
        # Use canonical pipeline tags from the science_tags table
        existing_labels_lower = {t.label.lower() for t in tag_infos}
        for ct in canonical_tags:
            if ct.label.lower() not in existing_labels_lower:
                tag_infos.append(ct)
    else:
        # Legacy fallback: promote high-confidence science attributes to tags
        # (used when canonical run hasn't completed yet)
        _TAG_THRESHOLD = 0.5
        _TAG_NAMESPACES = ("style.", "cognitive.")
        preloaded_lower = {t.label.lower() for t in tag_infos}

        for sa in science_attributes:
            key = sa.key
            is_tag_attr = (
                any(key.startswith(ns) for ns in _TAG_NAMESPACES)
                or "room_function" in key
            )
            if is_tag_attr and sa.value >= _TAG_THRESHOLD:
                label = _key_to_label(key)
                if label.lower() not in preloaded_lower:
                    tag_infos.append(TagInfo(
                        label=label,
                        source="science_pipeline",
                        source_label=_source_label_for(key),
                        confidence=sa.value,
                        attribute_key=key,
                    ))

    # ── Affordance scores: prefer canonical artifact, fall back to cache ──────
    aff_payload = affordance_payload
    if current_run is not None and current_run.status == "COMPLETED":
        from backend.models.science_runs import ScienceArtifact
        aff_artifact = (
            db.query(ScienceArtifact)
            .filter(
                ScienceArtifact.science_run_id == current_run.id,
                ScienceArtifact.artifact_type == "affordance_json",
            )
            .first()
        )
        if aff_artifact and aff_artifact.meta_json:
            aff_payload = aff_artifact.meta_json

        material_artifact = (
            db.query(ScienceArtifact)
            .filter(
                ScienceArtifact.science_run_id == current_run.id,
                ScienceArtifact.artifact_type == "materials_json",
            )
            .first()
        )
        if material_artifact and material_artifact.meta_json:
            material_payload = material_artifact.meta_json
            existing_keys = {a.key for a in science_attributes}
            materials = (
                material_payload.get("materials_aggregated")
                or material_payload.get("materials")
                or []
            )
            for material in materials[:8]:
                material_name = str(material.get("material", "unknown")).strip().lower()
                if not material_name:
                    continue
                pretty = " ".join(w.capitalize() for w in material_name.split("_"))
                coverage_3d_key = f"material.vlm.{material_name}_coverage_3d"
                coverage_2d_key = f"material.vlm.{material_name}_coverage_2d"
                coverage_3d = float(material.get("coverage_3d", material.get("coverage_2d", 0.0)))
                coverage_2d = float(material.get("coverage_2d", material.get("coverage", coverage_3d)))
                if coverage_3d_key not in existing_keys:
                    science_attributes.append(AttributeValue(
                        key=coverage_3d_key,
                        name=f"{pretty} Coverage (3D)",
                        category="Materials",
                        value=coverage_3d,
                        source="science_pipeline.materials",
                    ))
                    existing_keys.add(coverage_3d_key)
                if coverage_2d_key not in existing_keys:
                    science_attributes.append(AttributeValue(
                        key=coverage_2d_key,
                        name=f"{pretty} Coverage (2D)",
                        category="Materials",
                        value=coverage_2d,
                        source="science_pipeline.materials",
                    ))
                    existing_keys.add(coverage_2d_key)

    science_attributes.sort(key=lambda item: item.key)

    return ImageDetailResult(
        id=image.id,
        url=url,
        filename=filename,
        tags=tag_infos,
        meta_data=meta,
        affordance_scores=_score_list_from_map((aff_payload or {}).get("scores")),
        affordance_method=(aff_payload or {}).get("method"),
        science_attributes=science_attributes,
        human_validations=human_validations,
        science_run=run_info,
        canonical_outputs_available=canonical_outputs_available,
    )


@router.post("/science/bootstrap", response_model=BootstrapResponse)
def bootstrap_science(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user=Depends(require_tagger),
) -> BootstrapResponse:
    """Queue missing canonical science runs for all images.

    Called once per Explorer session on app mount. Returns immediately with
    a summary of what was queued. Actual pipeline processing runs in a
    background thread so the UI is never blocked.
    """
    from backend.services.science_runs import queue_missing_science_runs

    summary = queue_missing_science_runs(
        db,
        trigger_source="explorer_bootstrap",
        limit=500,
    )

    # Spawn a background thread to work through the queue.
    # Uses its own DB session to avoid sharing the request session.
    background_tasks.add_task(_run_pending_science_jobs)

    return BootstrapResponse(**summary)


@router.get("/science/status", response_model=ScienceStatusResponse)
def science_status(
    db: Session = Depends(get_db),
    user=Depends(require_tagger),
) -> ScienceStatusResponse:
    """Return aggregate progress for the active canonical science version."""
    from backend.services.science_runs import get_science_status

    status = get_science_status(db)
    return ScienceStatusResponse(**status)


def _run_pending_science_jobs() -> None:
    """Background worker: process PENDING science runs one at a time.

    Uses its own DB session so it does not interfere with request sessions.
    CPU-bound work runs in a thread (FastAPI BackgroundTasks run in the same
    event loop thread; we offload to a real OS thread here).
    """
    def _worker() -> None:
        from backend.models.science_runs import ScienceRun
        from backend.science.pipeline import SciencePipeline, SciencePipelineConfig
        from backend.services.science_runs import CANONICAL_CONFIG

        db = SessionLocal()
        try:
            config = SciencePipelineConfig.from_mapping(CANONICAL_CONFIG)
            pipeline = SciencePipeline(db=db, config=config)

            pending = (
                db.query(ScienceRun)
                .filter(ScienceRun.status == "PENDING")
                .order_by(ScienceRun.queued_at)
                .limit(100)
                .all()
            )

            logger.info("Science worker: processing %d pending runs.", len(pending))
            for run in pending:
                try:
                    pipeline.process_image_canonical(
                        run.image_id,
                        trigger_source=run.trigger_source,
                    )
                except Exception as exc:
                    logger.error(
                        "Science worker: unhandled error for image %d: %s",
                        run.image_id, exc,
                    )
        finally:
            db.close()

    t = threading.Thread(target=_worker, daemon=True, name="science-worker")
    t.start()


@router.get("/images/{image_id}/affordance")
def get_image_affordance(
    image_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_tagger),
):
    image = db.query(Image).filter(Image.id == image_id).first()
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found")
    payload = _get_or_compute_affordance_payload(image, db)
    return {
        "image_id": image_id,
        "affordance_scores": _score_list_from_map(payload.get("scores")),
        "affordance_method": payload.get("method"),
    }


@router.post("/seed")
def seed_sample_images(
    payload: Optional[dict] = None,
    db: Session = Depends(get_db),
    user=Depends(require_tagger),
):
    """Seed the DB with bundled sample image URLs from google_images_import.json.

    This is an explicit, user-initiated action intended for empty or low-data installs.
    """
    payload = payload or {}
    force = bool(payload.get("force"))
    existing = db.query(Image).count()
    if existing > 0 and not force:
        return {
            "ok": True,
            "skipped": True,
            "message": f"Database already has {existing} images; seeding skipped. Pass force=true to override.",
        }

    # Lazy import to avoid import-time DB setup costs
    from backend.scripts.import_images_from_json import import_images

    json_path = Path(__file__).resolve().parents[1] / "database" / "google_images_import.json"
    if not json_path.exists():
        raise HTTPException(status_code=500, detail=f"Seed file not found: {json_path}")

    result = import_images(str(json_path))
    return {"ok": True, "skipped": False, **result}
