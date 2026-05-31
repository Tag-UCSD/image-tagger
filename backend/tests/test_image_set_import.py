"""Import service tests for image sets (Track A, Task A2-3)."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault(
    "SUPABASE_JWT_SECRET",
    "image-set-import-test-secret",
)

_SQLITE_FILE = tempfile.NamedTemporaryFile(
    prefix="image_tagger_image_set_import_", suffix=".sqlite", delete=False
)
_SQLITE_FILE.close()
_SQLITE_PATH = Path(_SQLITE_FILE.name)
os.environ["DATABASE_URL"] = f"sqlite:///{_SQLITE_PATH}"

import backend.database.core as db_core
import backend.models  # noqa: F401
from backend.database.core import Base
from backend.models.assets import Image
from backend.models.image_sets import ImageSet, ImageSetItem
from backend.schemas.image_sets import ImageSetImportImage, ImageSetImportRequest
from backend.services.image_sets import import_image_set

_engine = sa.create_engine(
    f"sqlite:///{_SQLITE_PATH}",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
db_core.engine = _engine
db_core.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
Base.metadata.create_all(bind=_engine)
_Session = db_core.SessionLocal


def _three_image_request(*, slug: str = "a23-fixture") -> ImageSetImportRequest:
    return ImageSetImportRequest(
        name="A2-3 Three Image Fixture",
        slug=slug,
        description="Smoke import set",
        source="test_fixture",
        provenance={"fixture": "a2-3"},
        images=[
            ImageSetImportImage(
                filename="img_001.jpg",
                url="https://example.com/img_001.jpg",
                room_type="living_room",
                photographer="Alice",
                license="CC-BY-4.0",
                tags=["living room", "sofa"],
            ),
            ImageSetImportImage(
                filename="img_002.jpg",
                path="/data/fixtures/img_002.jpg",
                room_type="kitchen",
                photographer="Bob",
                tags=["kitchen"],
            ),
            ImageSetImportImage(
                filename="img_003.jpg",
                storage_path="s3://bucket/img_003.jpg",
                room_type="bedroom",
                source_url="https://example.com/img_003",
                license_url="https://creativecommons.org/licenses/by/4.0/",
            ),
        ],
    )


@pytest.fixture
def db() -> Session:
    session = _Session()
    try:
        yield session
        session.rollback()
    finally:
        session.close()


@pytest.fixture(autouse=True)
def _clean_tables(db: Session) -> None:
    db.query(ImageSetItem).delete()
    db.query(ImageSet).delete()
    db.query(Image).delete()
    db.commit()


def test_three_image_fixture_imports(db: Session) -> None:
    result = import_image_set(db, _three_image_request())

    assert result.slug == "a23-fixture"
    assert result.total_in_file == 3
    assert result.created_images == 3
    assert result.reused_images == 0
    assert result.created_items == 3
    assert result.skipped_items == 0
    assert result.errors == []

    images = db.query(Image).order_by(Image.filename).all()
    assert len(images) == 3
    assert images[0].meta_data["tags"] == ["living room", "sofa"]

    items = (
        db.query(ImageSetItem)
        .filter(ImageSetItem.image_set_id == result.image_set_id)
        .order_by(ImageSetItem.position)
        .all()
    )
    assert len(items) == 3
    assert items[0].room_type == "living_room"
    assert items[0].photographer == "Alice"
    assert items[0].license == "CC-BY-4.0"
    assert items[2].license_url == "https://creativecommons.org/licenses/by/4.0/"


def test_reimport_reports_reused_and_skipped_without_duplicates(db: Session) -> None:
    first = import_image_set(db, _three_image_request())
    second = import_image_set(db, _three_image_request())

    assert first.created_images == 3
    assert first.created_items == 3
    assert second.created_images == 0
    assert second.reused_images == 3
    assert second.created_items == 0
    assert second.skipped_items == 3
    assert second.errors == []

    assert db.query(Image).count() == 3
    assert db.query(ImageSetItem).count() == 3
    assert db.query(ImageSet).count() == 1


def test_bad_row_reported_while_good_rows_still_import(db: Session) -> None:
    request = ImageSetImportRequest(
        name="Partial Import",
        slug="a23-partial",
        images=[
            ImageSetImportImage(
                filename="good_a.jpg",
                url="https://example.com/good_a.jpg",
                room_type="office",
            ),
            ImageSetImportImage(
                filename="bad_row.jpg",
                url="https://example.com/bad_row.jpg",
                tags=["x"] * 101,
            ),
            ImageSetImportImage(
                filename="good_b.jpg",
                url="https://example.com/good_b.jpg",
                room_type="hallway",
            ),
        ],
    )

    result = import_image_set(db, request)

    assert result.total_in_file == 3
    assert result.created_images == 2
    assert result.created_items == 2
    assert len(result.errors) == 1
    assert result.errors[0].index == 1
    assert result.errors[0].filename == "bad_row.jpg"
    assert "too many tags" in result.errors[0].message

    assert db.query(Image).count() == 2
    assert db.query(ImageSetItem).count() == 2


def test_storage_path_identity_distinguishes_same_filename(db: Session) -> None:
    """Images match on filename + storage_path, not filename alone."""
    request = ImageSetImportRequest(
        name="Dual Path",
        slug="a23-dual-path",
        images=[
            ImageSetImportImage(
                filename="same.jpg",
                url="https://example.com/a/same.jpg",
            ),
            ImageSetImportImage(
                filename="same.jpg",
                url="https://example.com/b/same.jpg",
            ),
        ],
    )

    result = import_image_set(db, request)

    assert result.created_images == 2
    assert result.created_items == 2
    assert db.query(Image).count() == 2
