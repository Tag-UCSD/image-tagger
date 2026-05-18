"""Migration: add image_sets and image_set_items tables (Track A, Task A2-1).

Usage (inside the Docker ``api`` container)::

    python -m backend.scripts.migrate_3_5_00_add_image_set_tables

The script is idempotent and safe to run multiple times.
"""
from __future__ import annotations

import sys

from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

from backend.database.core import engine

logger_prefix = "[migrate_3_5_00]"


def _table_exists(table_name: str) -> bool:
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()


def _create_image_set_tables() -> None:
    ddl_image_sets = text("""
        CREATE TABLE IF NOT EXISTS image_sets (
            id          SERIAL PRIMARY KEY,
            slug        VARCHAR(128) NOT NULL,
            name        VARCHAR(255) NOT NULL,
            description TEXT,
            source      VARCHAR(255),
            provenance  JSONB,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at  TIMESTAMPTZ,
            CONSTRAINT uq_image_sets_slug UNIQUE (slug)
        )
    """)

    ddl_image_set_items = text("""
        CREATE TABLE IF NOT EXISTS image_set_items (
            id            SERIAL PRIMARY KEY,
            image_set_id  INTEGER NOT NULL REFERENCES image_sets(id) ON DELETE CASCADE,
            image_id      INTEGER NOT NULL REFERENCES images(id),
            position      INTEGER NOT NULL DEFAULT 0,
            room_type     VARCHAR(128),
            source_url    VARCHAR(512),
            photographer  VARCHAR(255),
            license       VARCHAR(255),
            license_url   VARCHAR(512),
            created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at    TIMESTAMPTZ,
            CONSTRAINT uq_image_set_items_set_image
                UNIQUE (image_set_id, image_id)
        )
    """)

    ddl_idx_items_set = text(
        "CREATE INDEX IF NOT EXISTS ix_image_set_items_image_set_id "
        "ON image_set_items(image_set_id)"
    )
    ddl_idx_items_image = text(
        "CREATE INDEX IF NOT EXISTS ix_image_set_items_image_id "
        "ON image_set_items(image_id)"
    )
    ddl_idx_sets_slug = text(
        "CREATE INDEX IF NOT EXISTS ix_image_sets_slug ON image_sets(slug)"
    )

    with engine.begin() as conn:
        conn.execute(ddl_image_sets)
        conn.execute(ddl_image_set_items)
        conn.execute(ddl_idx_items_set)
        conn.execute(ddl_idx_items_image)
        conn.execute(ddl_idx_sets_slug)


def main() -> int:
    try:
        print(f"{logger_prefix} Creating image set tables...")
        _create_image_set_tables()
        print(f"{logger_prefix} Tables created (or already existed).")
        print(f"{logger_prefix} Migration complete.")
        return 0
    except SQLAlchemyError as exc:
        print(f"{logger_prefix} Database error: {exc}")
        return 1
    except Exception as exc:
        print(f"{logger_prefix} Unexpected error: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
