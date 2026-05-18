"""Image-set import and browse contracts (Track A, Task A2-2)."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, conlist, model_validator


# Slug length matches ``ImageSet.slug`` (``String(128)``).
_SLUG_MAX_LEN = 128
_IMAGE_LIST_MAX = 1000


class ImageSetImportImage(BaseModel):
    """One manifest row for admin image-set import."""

    filename: str = Field(min_length=1, max_length=255)
    url: Optional[str] = Field(default=None, max_length=2048)
    path: Optional[str] = Field(default=None, max_length=2048)
    storage_path: Optional[str] = Field(default=None, max_length=2048)
    room_type: Optional[str] = Field(default=None, max_length=128)
    source_url: Optional[str] = Field(default=None, max_length=512)
    photographer: Optional[str] = Field(default=None, max_length=255)
    license: Optional[str] = Field(default=None, max_length=255)
    license_url: Optional[str] = Field(default=None, max_length=512)
    tags: List[str] = Field(default_factory=list)
    meta_data: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def require_location(self) -> ImageSetImportImage:
        has_location = any(
            value and str(value).strip()
            for value in (self.url, self.path, self.storage_path)
        )
        if not has_location:
            raise ValueError("One of url, path, or storage_path is required")
        return self


class ImageSetImportRequest(BaseModel):
    """Admin manifest payload for ``POST /v1/admin/image-sets/import``."""

    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=_SLUG_MAX_LEN)
    description: Optional[str] = Field(default=None, max_length=10_000)
    source: Optional[str] = Field(default=None, max_length=255)
    provenance: Optional[Dict[str, Any]] = None
    images: conlist(ImageSetImportImage, min_length=1, max_length=_IMAGE_LIST_MAX)  # type: ignore[valid-type]


class ImageSetImportRowError(BaseModel):
    """Per-row failure reported by the import service (A2-3)."""

    message: str
    index: Optional[int] = None
    filename: Optional[str] = None


class ImageSetImportResponse(BaseModel):
    """Import summary returned after processing a manifest."""

    image_set_id: int
    slug: str
    created_images: int = 0
    reused_images: int = 0
    created_items: int = 0
    skipped_items: int = 0
    errors: List[ImageSetImportRowError] = Field(default_factory=list)
    total_in_file: int = 0


class ImageSetSummary(BaseModel):
    """Explorer list entry for ``GET /v1/explorer/image-sets``."""

    id: int
    slug: str
    name: str
    description: Optional[str] = None
    source: Optional[str] = None
    item_count: int = 0
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ImageSetListResponse(BaseModel):
    items: List[ImageSetSummary] = Field(default_factory=list)


class ImageSetMembership(BaseModel):
    """Image-set membership and provenance on image detail (A2-7)."""

    id: int
    slug: str
    name: str
    room_type: Optional[str] = None
    source_url: Optional[str] = None
    photographer: Optional[str] = None
    license: Optional[str] = None
    license_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


__all__ = [
    "ImageSetImportImage",
    "ImageSetImportRequest",
    "ImageSetImportRowError",
    "ImageSetImportResponse",
    "ImageSetSummary",
    "ImageSetListResponse",
    "ImageSetMembership",
]
