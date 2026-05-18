"""Named image collections with per-item provenance (Track A, Task A2-1).

``ImageSet`` groups images under a stable ``slug`` for Explorer filtering and
admin import. ``ImageSetItem`` is the join row: it records ordering,
room type, and attribution fields that may differ per set membership.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, List, Optional

from sqlalchemy import ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.core import Base
from backend.database.mixins import TimestampMixin

if TYPE_CHECKING:
    from backend.models.assets import Image


class ImageSet(Base, TimestampMixin):
    """A named, importable collection of images."""

    __tablename__ = "image_sets"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    provenance: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)

    items: Mapped[List["ImageSetItem"]] = relationship(
        "ImageSetItem",
        back_populates="image_set",
        cascade="all, delete-orphan",
    )


class ImageSetItem(Base, TimestampMixin):
    """Membership of one image in a set, with item-level provenance."""

    __tablename__ = "image_set_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    image_set_id: Mapped[int] = mapped_column(
        ForeignKey("image_sets.id"),
        index=True,
    )
    image_id: Mapped[int] = mapped_column(ForeignKey("images.id"), index=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    room_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    photographer: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    license: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    license_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "image_set_id",
            "image_id",
            name="uq_image_set_items_set_image",
        ),
    )

    image_set: Mapped["ImageSet"] = relationship("ImageSet", back_populates="items")
    image: Mapped["Image"] = relationship("Image", back_populates="image_set_items")
