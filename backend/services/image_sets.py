"""Image-set manifest import (Track A, Task A2-3)."""
from __future__ import annotations

import logging
from typing import Tuple

from sqlalchemy.orm import Session

from backend.models.assets import Image
from backend.models.image_sets import ImageSet, ImageSetItem
from backend.schemas.image_sets import (
    ImageSetImportImage,
    ImageSetImportRequest,
    ImageSetImportResponse,
    ImageSetImportRowError,
)

logger = logging.getLogger(__name__)

# Per-row guardrail; rows above this are reported in ``errors`` without aborting the run.
MAX_TAGS_PER_ROW = 100


def _resolve_storage_path(row: ImageSetImportImage) -> str:
    """Prefer explicit storage_path, then path, then url."""
    for candidate in (row.storage_path, row.path, row.url):
        if candidate and str(candidate).strip():
            return str(candidate).strip()
    raise ValueError("One of url, path, or storage_path is required")


def _merge_meta(row: ImageSetImportImage) -> dict:
    """Build ``Image.meta_data``, preserving imported tags under ``tags``."""
    meta = dict(row.meta_data or {})
    if row.tags:
        existing = meta.get("tags")
        if not isinstance(existing, list):
            existing = []
        merged = list(existing)
        for tag in row.tags:
            if tag not in merged:
                merged.append(tag)
        meta["tags"] = merged
    return meta


def _merge_into_existing_meta(image: Image, meta: dict) -> None:
    """Merge manifest meta into an existing image without dropping prior keys."""
    current = dict(image.meta_data or {})
    for key, value in meta.items():
        if key == "tags":
            existing = current.get("tags")
            if not isinstance(existing, list):
                existing = []
            merged = list(existing)
            if isinstance(value, list):
                for tag in value:
                    if tag not in merged:
                        merged.append(tag)
            current["tags"] = merged
        else:
            current[key] = value
    image.meta_data = current


def _get_or_create_image_set(
    db: Session,
    request: ImageSetImportRequest,
) -> ImageSet:
    """Return the ``ImageSet`` for ``request.slug``, creating or updating metadata."""
    image_set = db.query(ImageSet).filter(ImageSet.slug == request.slug).one_or_none()
    if image_set is None:
        image_set = ImageSet(
            slug=request.slug,
            name=request.name,
            description=request.description,
            source=request.source,
            provenance=request.provenance,
        )
        db.add(image_set)
        db.flush()
        return image_set

    image_set.name = request.name
    image_set.description = request.description
    image_set.source = request.source
    image_set.provenance = request.provenance
    db.flush()
    return image_set


def _find_image(db: Session, filename: str, storage_path: str) -> Image | None:
    return (
        db.query(Image)
        .filter(Image.filename == filename, Image.storage_path == storage_path)
        .one_or_none()
    )


def _has_membership(db: Session, image_set_id: int, image_id: int) -> bool:
    return (
        db.query(ImageSetItem.id)
        .filter(
            ImageSetItem.image_set_id == image_set_id,
            ImageSetItem.image_id == image_id,
        )
        .first()
        is not None
    )


def _import_row(
    db: Session,
    *,
    image_set: ImageSet,
    row: ImageSetImportImage,
    position: int,
    slug: str,
) -> Tuple[bool, bool, bool]:
    """Import one manifest row inside a savepoint.

    Returns ``(image_created, image_reused, item_created)``.
    ``item_created`` is False when membership already exists (skipped).
    """
    if len(row.tags) > MAX_TAGS_PER_ROW:
        raise ValueError(f"too many tags (max {MAX_TAGS_PER_ROW})")

    storage_path = _resolve_storage_path(row)
    meta = _merge_meta(row)

    image = _find_image(db, row.filename, storage_path)
    image_created = False
    image_reused = False

    if image is None:
        image = Image(
            filename=row.filename,
            storage_path=storage_path,
            meta_data=meta,
            upload_batch_id=f"image_set:{slug}",
        )
        db.add(image)
        db.flush()
        image_created = True
    else:
        image_reused = True
        _merge_into_existing_meta(image, meta)
        db.flush()

    if _has_membership(db, image_set.id, image.id):
        return image_created, image_reused, False

    db.add(
        ImageSetItem(
            image_set_id=image_set.id,
            image_id=image.id,
            position=position,
            room_type=row.room_type,
            source_url=row.source_url,
            photographer=row.photographer,
            license=row.license,
            license_url=row.license_url,
        )
    )
    db.flush()
    return image_created, image_reused, True


def import_image_set(
    db: Session,
    request: ImageSetImportRequest,
) -> ImageSetImportResponse:
    """Import a collection manifest into ``ImageSet``, ``Image``, and ``ImageSetItem`` rows.

    Valid rows are persisted even when other rows fail. Duplicate images (same
    filename + storage_path) are reused; duplicate set membership is skipped.
    """
    created_images = 0
    reused_images = 0
    created_items = 0
    skipped_items = 0
    errors: list[ImageSetImportRowError] = []

    image_set = _get_or_create_image_set(db, request)

    for index, row in enumerate(request.images):
        try:
            with db.begin_nested():
                image_created, image_reused, item_created = _import_row(
                    db,
                    image_set=image_set,
                    row=row,
                    position=index,
                    slug=request.slug,
                )
        except Exception as exc:
            logger.warning(
                "image_set_import row failed slug=%s index=%s filename=%s: %s",
                request.slug,
                index,
                row.filename,
                exc,
            )
            errors.append(
                ImageSetImportRowError(
                    index=index,
                    filename=row.filename,
                    message=str(exc),
                )
            )
            continue

        if image_created:
            created_images += 1
        elif image_reused:
            reused_images += 1
        if item_created:
            created_items += 1
        else:
            skipped_items += 1

    db.commit()
    db.refresh(image_set)

    return ImageSetImportResponse(
        image_set_id=image_set.id,
        slug=image_set.slug,
        created_images=created_images,
        reused_images=reused_images,
        created_items=created_items,
        skipped_items=skipped_items,
        errors=errors,
        total_in_file=len(request.images),
    )
