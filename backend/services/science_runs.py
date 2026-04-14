"""
Science run service layer.

Provides the authoritative state machine for canonical pipeline execution:
- ensure_science_run()         — create or retrieve a run record
- queue_missing_science_runs() — find images that need canonical outputs
- mark_run_started/completed/failed() — lifecycle transitions
- get_current_run_for_image()  — fetch the active run for the detail API
- persist_science_tags()       — store canonical tags after a run
- persist_science_artifact()   — store structured summary or file metadata
- get_science_status()         — aggregate progress counts
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.models.assets import Image
from backend.models.science_runs import ScienceArtifact, ScienceRun, ScienceTag

logger = logging.getLogger("v3.services.science_runs")

# ── Active science version ─────────────────────────────────────────────────────
# Bump this string when the canonical pipeline config changes so that existing
# COMPLETED runs are not invalidated implicitly.
ACTIVE_SCIENCE_VERSION = "3.4.74-canonical-v2"

def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def build_canonical_config() -> dict:
    """Build the canonical config used for queueing and run fingerprinting.

    The cheap heuristic materials pass is enabled by default.
    Expensive material enrichers remain opt-in at process startup.
    """
    return {
        "enable_color": True,
        "enable_complexity": True,
        "enable_texture": True,
        "enable_fractals": True,
        "enable_spatial": True,
        "enable_affordance": True,
        "enable_room_detection": True,
        "enable_segmentation": False,
        "enable_cognitive": False,
        "enable_semantic": False,
        "enable_materials_basic": True,
        "enable_materials_vlm": _env_flag("SCIENCE_ENABLE_MATERIALS_VLM", default=False),
        "enable_clip_materials": _env_flag("SCIENCE_ENABLE_CLIP_MATERIALS", default=False),
    }


CANONICAL_CONFIG: dict = build_canonical_config()


def get_active_science_version() -> str:
    return ACTIVE_SCIENCE_VERSION


def get_config_fingerprint(config: dict | None = None) -> str:
    cfg = config if config is not None else CANONICAL_CONFIG
    raw = json.dumps(cfg, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ── Run lifecycle ──────────────────────────────────────────────────────────────

def ensure_science_run(
    db: Session,
    image_id: int,
    trigger_source: str = "manual_admin",
) -> ScienceRun:
    """Get or create a ScienceRun for the image at the active version/config.

    Idempotent: returns an existing COMPLETED run unchanged.
    Resets FAILED / STALE runs to PENDING for retry.
    """
    version = get_active_science_version()
    fingerprint = get_config_fingerprint()

    existing = (
        db.query(ScienceRun)
        .filter(
            ScienceRun.image_id == image_id,
            ScienceRun.science_version == version,
            ScienceRun.config_fingerprint == fingerprint,
        )
        .first()
    )

    if existing is not None:
        if existing.status == "COMPLETED":
            return existing
        if existing.status in ("FAILED", "STALE"):
            existing.status = "PENDING"
            existing.queued_at = datetime.now(timezone.utc)
            existing.started_at = None
            existing.completed_at = None
            existing.error_message = None
            existing.trigger_source = trigger_source
            db.add(existing)
            db.commit()
            db.refresh(existing)
        return existing

    run = ScienceRun(
        image_id=image_id,
        science_version=version,
        config_fingerprint=fingerprint,
        status="PENDING",
        queued_at=datetime.now(timezone.utc),
        trigger_source=trigger_source,
        is_current=True,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def queue_missing_science_runs(
    db: Session,
    image_ids: list[int] | None = None,
    trigger_source: str = "explorer_bootstrap",
    limit: int = 200,
) -> dict:
    """Find images without a current COMPLETED run and queue them.

    Returns a summary dict with counts.
    """
    version = get_active_science_version()
    fingerprint = get_config_fingerprint()

    if image_ids is None:
        all_ids = [row[0] for row in db.query(Image.id).all()]
    else:
        all_ids = list(image_ids)

    completed_ids = set(
        row[0]
        for row in db.query(ScienceRun.image_id)
        .filter(
            ScienceRun.science_version == version,
            ScienceRun.config_fingerprint == fingerprint,
            ScienceRun.status == "COMPLETED",
        )
        .all()
    )

    running_ids = set(
        row[0]
        for row in db.query(ScienceRun.image_id)
        .filter(
            ScienceRun.science_version == version,
            ScienceRun.config_fingerprint == fingerprint,
            ScienceRun.status == "RUNNING",
        )
        .all()
    )

    failed_ids = set(
        row[0]
        for row in db.query(ScienceRun.image_id)
        .filter(
            ScienceRun.science_version == version,
            ScienceRun.config_fingerprint == fingerprint,
            ScienceRun.status == "FAILED",
        )
        .all()
    )

    missing = [i for i in all_ids if i not in completed_ids and i not in running_ids]
    to_queue = missing[:limit]

    for image_id in to_queue:
        ensure_science_run(db, image_id, trigger_source=trigger_source)

    return {
        "science_version": version,
        "queued": len(to_queue),
        "already_current": len(completed_ids),
        "running": len(running_ids),
        "failed": len(failed_ids),
        "total_images": len(all_ids),
    }


def mark_run_started(db: Session, run_id: int) -> None:
    run = db.query(ScienceRun).filter(ScienceRun.id == run_id).first()
    if run:
        run.status = "RUNNING"
        run.started_at = datetime.now(timezone.utc)
        db.add(run)
        db.commit()


def mark_run_completed(db: Session, run_id: int) -> None:
    run = db.query(ScienceRun).filter(ScienceRun.id == run_id).first()
    if run:
        run.status = "COMPLETED"
        run.completed_at = datetime.now(timezone.utc)
        db.add(run)
        db.commit()


def mark_run_failed(db: Session, run_id: int, error: str) -> None:
    run = db.query(ScienceRun).filter(ScienceRun.id == run_id).first()
    if run:
        run.status = "FAILED"
        run.completed_at = datetime.now(timezone.utc)
        run.error_message = str(error)[:2000]
        db.add(run)
        db.commit()


def get_current_run_for_image(db: Session, image_id: int) -> ScienceRun | None:
    """Return the ScienceRun for the active version/config, or None."""
    version = get_active_science_version()
    fingerprint = get_config_fingerprint()
    return (
        db.query(ScienceRun)
        .filter(
            ScienceRun.image_id == image_id,
            ScienceRun.science_version == version,
            ScienceRun.config_fingerprint == fingerprint,
        )
        .first()
    )


# ── Output persistence ─────────────────────────────────────────────────────────

def persist_science_tags(
    db: Session,
    run_id: int,
    image_id: int,
    tags: list[dict],
) -> int:
    """Insert canonical tags for a completed run. Skips duplicates."""
    inserted = 0
    for t in tags:
        existing = (
            db.query(ScienceTag)
            .filter(
                ScienceTag.science_run_id == run_id,
                ScienceTag.image_id == image_id,
                ScienceTag.tag_key == t["tag_key"],
            )
            .first()
        )
        if existing:
            continue
        tag = ScienceTag(
            science_run_id=run_id,
            image_id=image_id,
            tag_key=t["tag_key"],
            label=t["label"],
            namespace=t["namespace"],
            confidence=t.get("confidence"),
            source_analyzer=t.get("source_analyzer"),
            attribute_key=t.get("attribute_key"),
            is_canonical=True,
        )
        db.add(tag)
        inserted += 1
    if inserted:
        db.commit()
    return inserted


def persist_science_artifact(
    db: Session,
    run_id: int,
    image_id: int,
    artifact_type: str,
    meta_json: dict | None = None,
    storage_path: str | None = None,
    content_type: str | None = None,
    artifact_version: str | None = None,
) -> ScienceArtifact:
    """Insert or update a canonical artifact record for a run."""
    existing = (
        db.query(ScienceArtifact)
        .filter(
            ScienceArtifact.science_run_id == run_id,
            ScienceArtifact.image_id == image_id,
            ScienceArtifact.artifact_type == artifact_type,
        )
        .first()
    )
    if existing:
        existing.meta_json = meta_json
        if storage_path is not None:
            existing.storage_path = storage_path
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing

    artifact = ScienceArtifact(
        science_run_id=run_id,
        image_id=image_id,
        artifact_type=artifact_type,
        storage_path=storage_path,
        content_type=content_type,
        artifact_version=artifact_version or get_active_science_version(),
        meta_json=meta_json,
    )
    db.add(artifact)
    db.commit()
    db.refresh(artifact)
    return artifact


def get_science_tags_for_run(
    db: Session,
    run_id: int,
    image_id: int,
) -> list[ScienceTag]:
    return (
        db.query(ScienceTag)
        .filter(
            ScienceTag.science_run_id == run_id,
            ScienceTag.image_id == image_id,
            ScienceTag.is_canonical.is_(True),
        )
        .order_by(ScienceTag.namespace, ScienceTag.tag_key)
        .all()
    )


# ── Status reporting ───────────────────────────────────────────────────────────

def get_science_status(db: Session) -> dict:
    """Aggregate status counts across all runs for the active version."""
    version = get_active_science_version()
    fingerprint = get_config_fingerprint()

    rows = (
        db.query(ScienceRun.status, func.count(ScienceRun.id))
        .filter(
            ScienceRun.science_version == version,
            ScienceRun.config_fingerprint == fingerprint,
        )
        .group_by(ScienceRun.status)
        .all()
    )

    counts = {status: count for status, count in rows}
    total_images = db.query(Image).count()

    return {
        "science_version": version,
        "config_fingerprint": fingerprint,
        "current_completed": counts.get("COMPLETED", 0),
        "pending": counts.get("PENDING", 0),
        "running": counts.get("RUNNING", 0),
        "failed": counts.get("FAILED", 0),
        "total_images": total_images,
    }
