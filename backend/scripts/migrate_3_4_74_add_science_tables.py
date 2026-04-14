"""Migration: add science_runs, science_artifacts, science_tags tables.

Also seeds the canonical attribute keys required by the new science pipeline
(affordance scores, room-type confidences) so that Validation FK constraints
are satisfied when the canonical pipeline writes these attributes.

Usage (inside the Docker `api` container):

    python -m backend.scripts.migrate_3_4_74_add_science_tables

The script is idempotent and safe to run multiple times.
"""
from __future__ import annotations

import logging
from typing import List

from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

from backend.database.core import engine

logger = logging.getLogger(__name__)

# ── New attribute keys that the canonical pipeline persists to Validation ─────
# These must exist in the attributes table before the pipeline can write
# Validation rows (FK constraint: validations.attribute_key → attributes.key).

CANONICAL_ATTRIBUTES = [
    # Affordance scores (raw 1-7 Likert scale, LightGBM regressors)
    {"key": "affordance.L059", "name": "Affordance: Sleep (Primary)", "category": "affordance", "level": "L2", "sources": "science_pipeline", "notes": "Environmental suitability for sleep/rest (1-7 scale, Hypersim-trained LightGBM)"},
    {"key": "affordance.L079", "name": "Affordance: Cook (Daily)", "category": "affordance", "level": "L2", "sources": "science_pipeline", "notes": "Environmental suitability for cooking (1-7 scale)"},
    {"key": "affordance.L091", "name": "Affordance: Computer Work (Solo)", "category": "affordance", "level": "L2", "sources": "science_pipeline", "notes": "Environmental suitability for focused computer work (1-7 scale)"},
    {"key": "affordance.L130", "name": "Affordance: Casual Conversation", "category": "affordance", "level": "L2", "sources": "science_pipeline", "notes": "Environmental suitability for conversation (1-7 scale)"},
    {"key": "affordance.L141", "name": "Affordance: Yoga / Stretching", "category": "affordance", "level": "L2", "sources": "science_pipeline", "notes": "Environmental suitability for yoga/movement (1-7 scale)"},
    # Normalized affordance scores (0-1 range for BN compatibility)
    {"key": "affordance.L059_norm", "name": "Affordance: Sleep (normalized)", "category": "affordance", "level": "L2", "sources": "science_pipeline", "notes": "Affordance L059 normalized to 0-1"},
    {"key": "affordance.L079_norm", "name": "Affordance: Cook (normalized)", "category": "affordance", "level": "L2", "sources": "science_pipeline", "notes": "Affordance L079 normalized to 0-1"},
    {"key": "affordance.L091_norm", "name": "Affordance: Work (normalized)", "category": "affordance", "level": "L2", "sources": "science_pipeline", "notes": "Affordance L091 normalized to 0-1"},
    {"key": "affordance.L130_norm", "name": "Affordance: Conversation (normalized)", "category": "affordance", "level": "L2", "sources": "science_pipeline", "notes": "Affordance L130 normalized to 0-1"},
    {"key": "affordance.L141_norm", "name": "Affordance: Yoga (normalized)", "category": "affordance", "level": "L2", "sources": "science_pipeline", "notes": "Affordance L141 normalized to 0-1"},
    # Room-type classification (Places365 → coarse taxonomy)
    {"key": "room.type_coarse", "name": "Room Type (coarse index)", "category": "spatial", "level": "L2", "sources": "science_pipeline", "notes": "Coarse room category index (Places365 → 13-class taxonomy)"},
    {"key": "room.type_coarse_confidence", "name": "Room Type Confidence (coarse)", "category": "spatial", "level": "L2", "sources": "science_pipeline", "notes": "Probability of primary coarse room class (0-1)"},
    {"key": "room.type_fine_confidence", "name": "Room Type Confidence (fine)", "category": "spatial", "level": "L2", "sources": "science_pipeline", "notes": "Probability of primary fine-grained Places365 class (0-1)"},
    {"key": "biophilia.index", "name": "Biophilia Index", "category": "biophilia", "level": "L2", "sources": "science_pipeline", "notes": "Weighted composite of lightweight plant-presence and natural-texture proxies."},
]


def _table_exists(table_name: str) -> bool:
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()


def _create_science_tables() -> None:
    ddl_science_runs = text("""
        CREATE TABLE IF NOT EXISTS science_runs (
            id                  SERIAL PRIMARY KEY,
            image_id            INTEGER NOT NULL REFERENCES images(id),
            science_version     VARCHAR(128) NOT NULL,
            config_fingerprint  VARCHAR(64)  NOT NULL,
            status              VARCHAR(32)  NOT NULL DEFAULT 'PENDING',
            queued_at           TIMESTAMPTZ,
            started_at          TIMESTAMPTZ,
            completed_at        TIMESTAMPTZ,
            error_message       TEXT,
            trigger_source      VARCHAR(64)  NOT NULL DEFAULT 'manual_admin',
            is_current          BOOLEAN      NOT NULL DEFAULT TRUE,
            created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMPTZ,
            CONSTRAINT uq_science_runs_image_version_config
                UNIQUE (image_id, science_version, config_fingerprint)
        )
    """)

    ddl_science_artifacts = text("""
        CREATE TABLE IF NOT EXISTS science_artifacts (
            id               SERIAL PRIMARY KEY,
            science_run_id   INTEGER NOT NULL REFERENCES science_runs(id) ON DELETE CASCADE,
            image_id         INTEGER NOT NULL REFERENCES images(id),
            artifact_type    VARCHAR(64)  NOT NULL,
            storage_path     VARCHAR(512),
            content_type     VARCHAR(64),
            artifact_version VARCHAR(64),
            meta_json        JSONB,
            created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at       TIMESTAMPTZ
        )
    """)

    ddl_science_tags = text("""
        CREATE TABLE IF NOT EXISTS science_tags (
            id               SERIAL PRIMARY KEY,
            science_run_id   INTEGER NOT NULL REFERENCES science_runs(id) ON DELETE CASCADE,
            image_id         INTEGER NOT NULL REFERENCES images(id),
            tag_key          VARCHAR(255) NOT NULL,
            label            VARCHAR(255) NOT NULL,
            namespace        VARCHAR(64)  NOT NULL,
            confidence       FLOAT,
            source_analyzer  VARCHAR(128),
            attribute_key    VARCHAR(255),
            is_canonical     BOOLEAN NOT NULL DEFAULT TRUE,
            created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at       TIMESTAMPTZ,
            CONSTRAINT uq_science_tags_run_image_tag
                UNIQUE (science_run_id, image_id, tag_key)
        )
    """)

    ddl_idx_runs_image = text(
        "CREATE INDEX IF NOT EXISTS ix_science_runs_image_id ON science_runs(image_id)"
    )
    ddl_idx_artifacts_run = text(
        "CREATE INDEX IF NOT EXISTS ix_science_artifacts_science_run_id ON science_artifacts(science_run_id)"
    )
    ddl_idx_artifacts_image = text(
        "CREATE INDEX IF NOT EXISTS ix_science_artifacts_image_id ON science_artifacts(image_id)"
    )
    ddl_idx_tags_run = text(
        "CREATE INDEX IF NOT EXISTS ix_science_tags_science_run_id ON science_tags(science_run_id)"
    )
    ddl_idx_tags_image = text(
        "CREATE INDEX IF NOT EXISTS ix_science_tags_image_id ON science_tags(image_id)"
    )

    with engine.begin() as conn:
        conn.execute(ddl_science_runs)
        conn.execute(ddl_science_artifacts)
        conn.execute(ddl_science_tags)
        conn.execute(ddl_idx_runs_image)
        conn.execute(ddl_idx_artifacts_run)
        conn.execute(ddl_idx_artifacts_image)
        conn.execute(ddl_idx_tags_run)
        conn.execute(ddl_idx_tags_image)


def _seed_canonical_attributes() -> int:
    """Insert canonical attribute rows with ON CONFLICT DO NOTHING."""
    inserted = 0
    with engine.begin() as conn:
        for attr in CANONICAL_ATTRIBUTES:
            result = conn.execute(
                text("""
                    INSERT INTO attributes (key, name, category, level, sources, notes, is_active)
                    VALUES (:key, :name, :category, :level, :sources, :notes, TRUE)
                    ON CONFLICT (key) DO NOTHING
                """),
                {
                    "key": attr["key"],
                    "name": attr["name"],
                    "category": attr.get("category"),
                    "level": attr.get("level"),
                    "sources": attr.get("sources"),
                    "notes": attr.get("notes"),
                },
            )
            if result.rowcount:
                inserted += 1
    return inserted


def main() -> int:
    try:
        print("[migrate_3_4_74] Creating science tables...")
        _create_science_tables()
        print("[migrate_3_4_74] Tables created (or already existed).")

        print("[migrate_3_4_74] Seeding canonical attribute keys...")
        n = _seed_canonical_attributes()
        print(f"[migrate_3_4_74] Inserted {n} new attribute rows (skipped existing).")

        print("[migrate_3_4_74] Migration complete.")
        return 0

    except SQLAlchemyError as exc:
        print(f"[migrate_3_4_74] Database error: {exc}")
        return 1
    except Exception as exc:
        print(f"[migrate_3_4_74] Unexpected error: {exc}")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
