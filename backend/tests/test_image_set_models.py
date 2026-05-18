"""ORM tests for ImageSet / ImageSetItem (Track A, Task A2-1)."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault(
    "SUPABASE_JWT_SECRET",
    "image-set-model-test-secret",
)

_SQLITE_FILE = tempfile.NamedTemporaryFile(
    prefix="image_tagger_image_set_models_", suffix=".sqlite", delete=False
)
_SQLITE_FILE.close()
_SQLITE_PATH = Path(_SQLITE_FILE.name)
os.environ["DATABASE_URL"] = f"sqlite:///{_SQLITE_PATH}"

import backend.database.core as db_core
import backend.models  # noqa: F401 — register tables on Base.metadata
from backend.database.core import Base
from backend.models.assets import Image
from backend.models.image_sets import ImageSet, ImageSetItem

_engine = sa.create_engine(
    f"sqlite:///{_SQLITE_PATH}",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
db_core.engine = _engine
db_core.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
Base.metadata.create_all(bind=_engine)
_Session = db_core.SessionLocal


@pytest.fixture
def db() -> Session:
    session = _Session()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def test_create_set_attach_images_commit_reload_provenance(db: Session) -> None:
    """Create a set, attach images, commit, reload, and read provenance."""
    image_set = ImageSet(
        slug="hypersim-living-rooms",
        name="Hypersim Living Rooms",
        description="Curated living-room subset",
        source="hypersim",
        provenance={"manifest_version": "1.0", "imported_by": "test"},
    )
    db.add(image_set)
    db.flush()

    img_a = Image(
        filename="living_001.jpg",
        storage_path="/data/hypersim/living_001.jpg",
        meta_data={},
    )
    img_b = Image(
        filename="living_002.jpg",
        storage_path="/data/hypersim/living_002.jpg",
        meta_data={},
    )
    db.add_all([img_a, img_b])
    db.flush()

    db.add_all(
        [
            ImageSetItem(
                image_set_id=image_set.id,
                image_id=img_a.id,
                position=0,
                room_type="living_room",
                source_url="https://example.com/photos/living_001.jpg",
                photographer="Jane Doe",
                license="CC-BY-4.0",
                license_url="https://creativecommons.org/licenses/by/4.0/",
            ),
            ImageSetItem(
                image_set_id=image_set.id,
                image_id=img_b.id,
                position=1,
                room_type="living_room",
                source_url="https://example.com/photos/living_002.jpg",
                photographer="John Smith",
                license="CC0-1.0",
                license_url="https://creativecommons.org/publicdomain/zero/1.0/",
            ),
        ]
    )
    db.commit()

    set_id = image_set.id
    db.expire_all()

    reloaded = db.get(ImageSet, set_id)
    assert reloaded is not None
    assert reloaded.slug == "hypersim-living-rooms"
    assert reloaded.provenance == {
        "manifest_version": "1.0",
        "imported_by": "test",
    }
    assert len(reloaded.items) == 2

    by_position = sorted(reloaded.items, key=lambda item: item.position)
    first = by_position[0]
    assert first.room_type == "living_room"
    assert first.photographer == "Jane Doe"
    assert first.license == "CC-BY-4.0"
    assert first.license_url == "https://creativecommons.org/licenses/by/4.0/"
    assert first.source_url == "https://example.com/photos/living_001.jpg"
    assert first.image.filename == "living_001.jpg"


def test_duplicate_slug_rejected(db: Session) -> None:
    db.add(
        ImageSet(slug="duplicate-slug", name="First"),
    )
    db.commit()

    db.add(
        ImageSet(slug="duplicate-slug", name="Second"),
    )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_duplicate_membership_rejected(db: Session) -> None:
    """The (image_set_id, image_id) pair must be unique."""
    image_set = ImageSet(slug="membership-dup", name="Dup Test")
    image = Image(
        filename="dup.jpg",
        storage_path="/data/dup.jpg",
        meta_data={},
    )
    db.add_all([image_set, image])
    db.commit()

    db.add(
        ImageSetItem(
            image_set_id=image_set.id,
            image_id=image.id,
            position=0,
            room_type="bedroom",
        )
    )
    db.commit()

    db.add(
        ImageSetItem(
            image_set_id=image_set.id,
            image_id=image.id,
            position=1,
            room_type="bedroom",
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_image_can_belong_to_multiple_sets(db: Session) -> None:
    image = Image(
        filename="shared.jpg",
        storage_path="/data/shared.jpg",
        meta_data={},
    )
    set_a = ImageSet(slug="set-a", name="Set A")
    set_b = ImageSet(slug="set-b", name="Set B")
    db.add_all([image, set_a, set_b])
    db.commit()

    db.add_all(
        [
            ImageSetItem(
                image_set_id=set_a.id,
                image_id=image.id,
                position=0,
                room_type="office",
            ),
            ImageSetItem(
                image_set_id=set_b.id,
                image_id=image.id,
                position=0,
                room_type="workspace",
            ),
        ]
    )
    db.commit()

    db.refresh(image)
    assert len(image.image_set_items) == 2
    room_types = {item.room_type for item in image.image_set_items}
    assert room_types == {"office", "workspace"}
