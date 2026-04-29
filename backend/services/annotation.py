from sqlalchemy.orm import Session
from sqlalchemy import select, func
from backend.database.core import Base
from backend.models.assets import Image, Region
from backend.models.annotation import Validation
from backend.schemas.annotation import ValidationRequest, RegionCreateRequest
import logging

logger = logging.getLogger("v3.services.annotation")

class AnnotationService:
    """
    Business Logic for the Tagger Workbench.
    Handles the 'Flow' state (getting the next image) and 'Persistence' (saving tags).
    """

    def __init__(self, db: Session):
        self.db = db

    def get_next_image_for_user(self, user_id: int) -> Image | None:
        """
        PRIORITY QUEUE LOGIC:
        1. Find images assigned to the user's current batch (if any).
        2. Fallback: Find images with FEWEST validations (to ensure coverage).
        3. Filter out images this user has already validated.
        """
        # Subquery: Images ID validated by THIS user
        validated_ids = select(Validation.image_id).where(Validation.user_id == user_id)

        # Main Query: Images NOT in subquery, ordered by validation count (asc)
        stmt = (
            select(Image)
            .outerjoin(Validation, Image.id == Validation.image_id)
            .where(Image.id.not_in(validated_ids))
            .group_by(Image.id)
            .order_by(func.count(Validation.id).asc())
            .limit(1)
        )
        
        result = self.db.execute(stmt).scalar_one_or_none()
        return result

    def create_validation(self, user_id: int, data: ValidationRequest) -> Validation:
        """Record a human judgment.

        Mutating writes are wrapped in ``try/except`` with explicit
        ``self.db.rollback()`` on failure (Task A-4) so the session is
        never left in a half-committed state when the caller catches
        the re-raised exception.
        """
        new_val = Validation(
            user_id=user_id,
            image_id=data.image_id,
            attribute_key=data.attribute_key,
            value=data.value,
            duration_ms=data.duration_ms,
        )

        self.db.add(new_val)
        try:
            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            logger.exception("create_validation: commit failed: %s", exc)
            raise
        self.db.refresh(new_val)
        return new_val

    def create_region(self, user_id: int, data: RegionCreateRequest) -> Region:
        """Record a manual segmentation (bounding box / polygon).

        Mutating writes are wrapped in ``try/except`` with explicit
        ``self.db.rollback()`` on failure (Task A-4).
        """
        new_region = Region(
            image_id=data.image_id,
            geometry=data.geometry,
            manual_label=data.manual_label,
        )

        self.db.add(new_region)
        try:
            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            logger.exception("create_region: commit failed: %s", exc)
            raise
        self.db.refresh(new_region)
        return new_region