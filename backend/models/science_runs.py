"""
Science run orchestration models.

Three tables track canonical pipeline lifecycle:

- science_runs: one row per image per science version/config; authoritative
  lifecycle state (PENDING → RUNNING → COMPLETED | FAILED | STALE).
- science_artifacts: metadata for saved canonical outputs (JSON summaries,
  segmentation artifacts). Binary files stored on disk, not in DB.
- science_tags: canonical pipeline-derived tags generated once at run time;
  avoids ad-hoc tag synthesis in the API layer.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey, JSON,
    String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.core import Base
from backend.database.mixins import TimestampMixin


class ScienceRun(Base, TimestampMixin):
    """One canonical pipeline execution per image per science version/config."""

    __tablename__ = "science_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    image_id: Mapped[int] = mapped_column(ForeignKey("images.id"), index=True)
    science_version: Mapped[str] = mapped_column(String(128))
    config_fingerprint: Mapped[str] = mapped_column(String(64))

    # Lifecycle: PENDING → RUNNING → COMPLETED | FAILED | STALE
    status: Mapped[str] = mapped_column(String(32), default="PENDING")

    queued_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Where the run was triggered from
    trigger_source: Mapped[str] = mapped_column(
        String(64), default="manual_admin"
    )  # explorer_bootstrap | upload_job | manual_admin | backfill

    # Only one run should be "current" per image at a given version/config
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (
        UniqueConstraint(
            "image_id", "science_version", "config_fingerprint",
            name="uq_science_runs_image_version_config",
        ),
    )

    # Relationships
    image = relationship("Image", backref="science_runs")
    artifacts: Mapped[list["ScienceArtifact"]] = relationship(
        "ScienceArtifact", back_populates="science_run", cascade="all, delete-orphan"
    )
    tags: Mapped[list["ScienceTag"]] = relationship(
        "ScienceTag", back_populates="science_run", cascade="all, delete-orphan"
    )


class ScienceArtifact(Base, TimestampMixin):
    """Metadata for a canonical artifact produced by a science run.

    Binary files (PNGs, etc.) live on disk; only the path is stored here.
    Structured JSON summaries (affordance scores, room top-k, object counts)
    are stored in meta_json for easy retrieval without hitting the filesystem.
    """

    __tablename__ = "science_artifacts"

    id: Mapped[int] = mapped_column(primary_key=True)
    science_run_id: Mapped[int] = mapped_column(
        ForeignKey("science_runs.id"), index=True
    )
    image_id: Mapped[int] = mapped_column(ForeignKey("images.id"), index=True)

    # e.g. "affordance_json", "room_json", "segmentation_json", "segmentation_mask_png"
    artifact_type: Mapped[str] = mapped_column(String(64))

    # Filesystem / object-storage path (nullable for in-DB artifacts)
    storage_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    content_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    artifact_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Structured summary stored directly in DB
    meta_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    science_run = relationship("ScienceRun", back_populates="artifacts")


class ScienceTag(Base, TimestampMixin):
    """A canonical pipeline-derived tag, generated once at run time.

    Explorer reads from this table instead of synthesising tags on-the-fly
    in the API layer. Imported (preloaded) tags remain in Image.meta_data.
    """

    __tablename__ = "science_tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    science_run_id: Mapped[int] = mapped_column(
        ForeignKey("science_runs.id"), index=True
    )
    image_id: Mapped[int] = mapped_column(ForeignKey("images.id"), index=True)

    # e.g. "room_type.kitchen", "affordance.l091.high", "object.chair"
    tag_key: Mapped[str] = mapped_column(String(255))
    # Human-readable display label
    label: Mapped[str] = mapped_column(String(255))
    # Top-level namespace: "room_type" | "affordance" | "object" | "style" | "cognitive"
    namespace: Mapped[str] = mapped_column(String(64))

    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    source_analyzer: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    # Link back to the attribute key that produced this tag (if applicable)
    attribute_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_canonical: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (
        UniqueConstraint(
            "science_run_id", "image_id", "tag_key",
            name="uq_science_tags_run_image_tag",
        ),
    )

    science_run = relationship("ScienceRun", back_populates="tags")
