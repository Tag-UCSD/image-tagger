#!/usr/bin/env python3
"""
TRS-905 & TRS-906: Schema migration and definition quality improvement.

Provides:
- Database schema migrations
- Tag definition quality improvement suggestions

Usage:
    # Check for pending migrations
    python scripts/db_migrate.py status
    
    # Run pending migrations
    python scripts/db_migrate.py upgrade
    
    # Improve definitions
    python scripts/db_migrate.py improve-definitions v0.2.8
"""

from __future__ import annotations
import argparse
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent

sys.path.insert(0, str(REPO_ROOT))
from backend.app.db import get_db


# ============================================================================
# Schema Migrations
# ============================================================================

MIGRATIONS = [
    {
        "version": 1,
        "name": "initial_schema",
        "sql": """
        -- This is the initial schema, already applied via schema.sql
        -- Included here for migration tracking
        SELECT 1;
        """,
    },
    {
        "version": 2,
        "name": "add_proposal_priority",
        "sql": """
        ALTER TABLE proposals ADD COLUMN priority INTEGER DEFAULT 0;
        """,
    },
    {
        "version": 3,
        "name": "add_release_checksum",
        "sql": """
        ALTER TABLE releases ADD COLUMN contracts_sha256 TEXT;
        """,
    },
    {
        "version": 4,
        "name": "add_api_key_scopes",
        "sql": """
        ALTER TABLE api_keys ADD COLUMN scopes TEXT;
        """,
    },
    {
        "version": 5,
        "name": "add_audit_metadata",
        "sql": """
        ALTER TABLE audit_log ADD COLUMN metadata TEXT;
        """,
    },
]


def get_current_version(conn: sqlite3.Connection) -> int:
    """Get current schema version."""
    try:
        row = conn.execute(
            "SELECT value FROM settings WHERE key = 'schema_version'"
        ).fetchone()
        return int(row[0]) if row else 0
    except sqlite3.OperationalError:
        return 0


def set_version(conn: sqlite3.Connection, version: int) -> None:
    """Set schema version."""
    conn.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES ('schema_version', ?)",
        (str(version),)
    )


def cmd_status(args):
    """Show migration status."""
    db = get_db()
    
    with db._connect() as conn:
        current = get_current_version(conn)
    
    print(f"Current schema version: {current}")
    print(f"Available migrations: {len(MIGRATIONS)}")
    print()
    
    for migration in MIGRATIONS:
        status = "✅" if migration["version"] <= current else "⏳"
        print(f"  {status} v{migration['version']}: {migration['name']}")
    
    pending = [m for m in MIGRATIONS if m["version"] > current]
    if pending:
        print()
        print(f"Pending migrations: {len(pending)}")
    
    return 0


def cmd_upgrade(args):
    """Run pending migrations."""
    db = get_db()
    
    with db._connect() as conn:
        current = get_current_version(conn)
        
        pending = [m for m in MIGRATIONS if m["version"] > current]
        
        if not pending:
            print("No pending migrations.")
            return 0
        
        print(f"Running {len(pending)} migrations...")
        
        for migration in pending:
            print(f"  Applying v{migration['version']}: {migration['name']}...")
            
            if args.dry_run:
                print("    (dry run)")
                continue
            
            try:
                conn.executescript(migration["sql"])
                set_version(conn, migration["version"])
                print("    Done")
            except sqlite3.OperationalError as e:
                # Some migrations might fail if column already exists
                if "duplicate column" in str(e).lower():
                    print(f"    Skipped (already applied)")
                    set_version(conn, migration["version"])
                else:
                    print(f"    ERROR: {e}")
                    return 1
    
    print()
    print("Migrations complete!")
    return 0


# ============================================================================
# Definition Improvement
# ============================================================================

def load_registry(version: str) -> dict:
    """Load registry for a version."""
    registry_dir = REPO_ROOT / "core" / "trs-core" / version / "registry"
    yamls = sorted(list(registry_dir.glob("*.yml")) + list(registry_dir.glob("*.yaml")))
    if not yamls:
        raise FileNotFoundError(f"No registry YAML in {registry_dir}")
    return yaml.safe_load(yamls[0].read_text(encoding="utf-8"))


def generate_definition(tag_id: str, tag: dict) -> str:
    """Generate an improved definition for a tag."""
    name = tag.get("canonical_name", tag_id)
    domain = tag.get("domain", "")
    category = tag.get("category", "")
    value_type = tag.get("value_type", "")
    
    # Build definition based on available information
    parts = []
    
    # Main description
    if "lighting" in tag_id.lower() or "luminous" in domain.lower():
        parts.append(f"Quantifies {name.lower()} characteristics of the lighting environment")
    elif "color" in tag_id.lower():
        parts.append(f"Measures {name.lower()} properties of color in the space")
    elif "spatial" in tag_id.lower() or "geometry" in domain.lower():
        parts.append(f"Characterizes {name.lower()} aspects of spatial configuration")
    elif "biophil" in tag_id.lower():
        parts.append(f"Assesses {name.lower()} presence of biophilic design elements")
    elif "social" in tag_id.lower():
        parts.append(f"Evaluates {name.lower()} social and privacy characteristics")
    elif "affect" in tag_id.lower():
        parts.append(f"Captures the perceived {name.lower()} quality of the environment")
    else:
        parts.append(f"Measures {name.lower()} attributes of the built environment")
    
    # Add value type context
    if value_type == "binary":
        parts.append("Expressed as presence or absence")
    elif value_type == "ordinal":
        parts.append("Rated on an ordered scale")
    elif value_type == "continuous":
        parts.append("Measured as a continuous value")
    
    return ". ".join(parts) + "."


def cmd_improve_definitions(args):
    """Generate improved definitions for tags."""
    version = args.version
    
    print(f"Loading {version}...")
    registry = load_registry(version)
    tags = registry.get("tags", {})
    
    improvements = []
    
    for tag_id, tag in tags.items():
        if not isinstance(tag, dict):
            continue
        
        definition = tag.get("definition", "")
        
        # Check if needs improvement
        needs_improvement = False
        
        if not definition:
            needs_improvement = True
        elif "operational tag" in definition.lower():
            needs_improvement = True
        elif len(definition) < 20:
            needs_improvement = True
        
        if needs_improvement:
            new_definition = generate_definition(tag_id, tag)
            improvements.append({
                "tag_id": tag_id,
                "old_definition": definition,
                "new_definition": new_definition,
            })
    
    print(f"Found {len(improvements)} tags needing improvement")
    print()
    
    # Show samples
    for imp in improvements[:10]:
        print(f"Tag: {imp['tag_id']}")
        print(f"  Old: {imp['old_definition'][:60]}...")
        print(f"  New: {imp['new_definition'][:60]}...")
        print()
    
    if len(improvements) > 10:
        print(f"... and {len(improvements) - 10} more")
    
    # Output
    if args.output:
        import json
        Path(args.output).write_text(
            json.dumps(improvements, indent=2),
            encoding="utf-8"
        )
        print(f"\nImprovements written to {args.output}")
    
    return 0


def main():
    parser = argparse.ArgumentParser(description="Database migrations and data improvement")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # status
    p_status = subparsers.add_parser("status", help="Show migration status")
    p_status.set_defaults(func=cmd_status)
    
    # upgrade
    p_upgrade = subparsers.add_parser("upgrade", help="Run pending migrations")
    p_upgrade.add_argument("--dry-run", action="store_true", help="Don't apply changes")
    p_upgrade.set_defaults(func=cmd_upgrade)
    
    # improve-definitions
    p_improve = subparsers.add_parser("improve-definitions", help="Generate improved definitions")
    p_improve.add_argument("version", help="Registry version")
    p_improve.add_argument("--output", "-o", help="Output JSON file")
    p_improve.set_defaults(func=cmd_improve_definitions)
    
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
