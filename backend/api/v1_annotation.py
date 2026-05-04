from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database.core import get_db
from backend.services.storage import to_static_path
from backend.services.annotation import AnnotationService
from backend.services.auth import CurrentUser, require_tagger
from backend.schemas.annotation import (
    ValidationRequest,
    ValidationResponse,
    RegionCreateRequest,
    ImageWorkItem,
)

router = APIRouter(
    prefix="/v1/workbench",
    tags=["Tagger Workbench"],
    responses={404: {"description": "Not found"}},
)


def _resolve_db_user_id(current_user: CurrentUser) -> Optional[int]:
    """Best-effort mapping from JWT-sourced ``CurrentUser.id`` to ``users.id``.

    ``CurrentUser.id`` is the Supabase JWT ``sub`` claim (a UUID string) or
    a synthetic ``dev:<role>`` token in development. ``Validation.user_id``
    is an integer FK to ``users.id``, so we only forward the value when it
    is parseable as an int. Otherwise we record ``None`` (the FK column is
    nullable) until the deferred User-upsert work lands. Returning ``None``
    keeps the workbench routes responsive instead of 500-ing on every
    JWT-authenticated request.
    """
    raw = current_user.id
    if raw and raw.isdigit():
        return int(raw)
    return None


@router.get("/next", response_model=ImageWorkItem)
async def get_next_image(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_tagger),
):
    """
    WORKBENCH CORE: Fetches the next image for the user to annotate.
    Uses the 'Least Validated' queue algorithm.
    """
    service = AnnotationService(db)
    image = service.get_next_image_for_user(_resolve_db_user_id(current_user))

    if not image:
        raise HTTPException(status_code=404, detail="No more images in queue")

    return ImageWorkItem(
        id=image.id,
        filename=image.filename,
        url=f"/static/{to_static_path(image.storage_path)}",
        meta_data=image.meta_data,
        created_at=image.created_at,
    )


@router.post("/validate", response_model=ValidationResponse)
async def submit_validation(
    payload: ValidationRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_tagger),
):
    """
    HITL: Submit a judgment on an attribute (e.g., "This is Modern: 0.9").
    """
    service = AnnotationService(db)
    result = service.create_validation(_resolve_db_user_id(current_user), payload)

    return ValidationResponse(
        id=result.id,
        created_at=result.created_at,
        status="success",
    )


@router.post("/region", status_code=201)
async def create_region(
    payload: RegionCreateRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_tagger),
):
    """
    HITL: Submit a new manual segmentation (box/polygon).
    """
    service = AnnotationService(db)
    result = service.create_region(_resolve_db_user_id(current_user), payload)

    return {
        "id": result.id,
        "status": "created",
        "label": result.manual_label,
    }