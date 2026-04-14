#!/usr/bin/env python3
"""
TRS-903: Registry migration tool.

Migrate registry from one version structure to another.

Usage:
    # Create new version from existing
    python scripts/migrate.py v0.2.8 v0.2.9
    
    # Apply migrations
    python scripts/migrate.py v0.2.8 v0.2.9 --apply-migrations
    
    # List available migrations
    python scripts/migrate.py --list-migrations
"""

from __future__ import annotations
import argparse
import copy
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
CORE_DIR = REPO_ROOT / "core" / "trs-core"


# ============================================================================
# Migrations
# ============================================================================

MIGRATIONS = {
    "add_version_added": {
        "description": "Add version_added field to tags missing it",
        "applies_to": ["v0.2.*", "v0.3.*"],
        "function": "migration_add_version_added",
    },
    "normalize_extractability": {
        "description": "Normalize extractability values (yes/no/partial)",
        "applies_to": ["v0.2.*"],
        "function": "migration_normalize_extractability",
    },
    "fix_placeholder_definitions": {
        "description": "Replace placeholder definitions with proper format",
        "applies_to": ["v0.2.*"],
        "function": "migration_fix_placeholder_definitions",
    },
    "add_missing_status": {
        "description": "Add status=active to tags missing status",
        "applies_to": ["v0.2.*"],
        "function": "migration_add_missing_status",
    },
}


def migration_add_version_added(registry: dict, target_version: str) -> int:
    """Add version_added to tags missing it."""
    count = 0
    for tag_id, tag in registry.get("tags", {}).items():
        if isinstance(tag, dict) and not tag.get("version_added"):
            tag["version_added"] = target_version
            count += 1
    return count


def migration_normalize_extractability(registry: dict, target_version: str) -> int:
    """Normalize extractability values."""
    valid_values = {"yes", "no", "partial", "n/a"}
    count = 0
    
    for tag_id, tag in registry.get("tags", {}).items():
        if not isinstance(tag, dict):
            continue
        
        extract = tag.get("extractability", {})
        if not isinstance(extract, dict):
            continue
        
        for key in ["from_2d", "from_3d_vr", "monocular_3d_approx"]:
            value = extract.get(key)
            if value and str(value).lower() not in valid_values:
                # Normalize
                normalized = str(value).lower().strip()
                if normalized in ("true", "1"):
                    extract[key] = "yes"
                elif normalized in ("false", "0"):
                    extract[key] = "no"
                elif "partial" in normalized:
                    extract[key] = "partial"
                else:
                    extract[key] = "n/a"
                count += 1
    
    return count


def migration_fix_placeholder_definitions(registry: dict, target_version: str) -> int:
    """Fix placeholder definitions."""
    count = 0
    
    for tag_id, tag in registry.get("tags", {}).items():
        if not isinstance(tag, dict):
            continue
        
        definition = tag.get("definition", "")
        
        if "operational tag" in definition.lower():
            # Generate better placeholder
            name = tag.get("canonical_name", tag_id)
            tag["definition"] = f"Measures {name.lower()} attributes of the environment."
            tag["version_modified"] = target_version
            count += 1
    
    return count


def migration_add_missing_status(registry: dict, target_version: str) -> int:
    """Add status to tags missing it."""
    count = 0
    
    for tag_id, tag in registry.get("tags", {}).items():
        if isinstance(tag, dict) and not tag.get("status"):
            tag["status"] = "active"
            count += 1
    
    return count


# ============================================================================
# Migration Runner
# ============================================================================

def run_migration(name: str, registry: dict, target_version: str) -> int:
    """Run a named migration."""
    if name not in MIGRATIONS:
        raise ValueError(f"Unknown migration: {name}")
    
    migration = MIGRATIONS[name]
    func_name = migration["function"]
    
    # Get function from globals
    func = globals().get(func_name)
    if not func:
        raise ValueError(f"Migration function not found: {func_name}")
    
    return func(registry, target_version)


def load_registry(version: str) -> dict:
    """Load registry for a version."""
    registry_dir = CORE_DIR / version / "registry"
    yamls = sorted(list(registry_dir.glob("*.yml")) + list(registry_dir.glob("*.yaml")))
    if not yamls:
        raise FileNotFoundError(f"No registry YAML in {registry_dir}")
    return yaml.safe_load(yamls[0].read_text(encoding="utf-8"))


def save_registry(registry: dict, version: str) -> Path:
    """Save registry to version directory."""
    registry_dir = CORE_DIR / version / "registry"
    registry_dir.mkdir(parents=True, exist_ok=True)
    
    reg_path = registry_dir / "trs_registry.yaml"
    
    yaml_content = yaml.dump(
        registry,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
        width=120,
    )
    reg_path.write_text(yaml_content, encoding="utf-8")
    
    return reg_path


def main():
    parser = argparse.ArgumentParser(description="Registry migration tool")
    parser.add_argument("source_version", nargs="?", help="Source version")
    parser.add_argument("target_version", nargs="?", help="Target version")
    parser.add_argument("--list-migrations", action="store_true", help="List migrations")
    parser.add_argument("--apply-migrations", action="store_true", help="Apply migrations")
    parser.add_argument("--migration", action="append", help="Specific migration to run")
    parser.add_argument("--dry-run", action="store_true", help="Don't save changes")
    args = parser.parse_args()

    # List migrations
    if args.list_migrations:
        print("Available Migrations:")
        print()
        for name, info in MIGRATIONS.items():
            print(f"  {name}")
            print(f"    {info['description']}")
            print(f"    Applies to: {', '.join(info['applies_to'])}")
            print()
        return 0
    
    # Require versions
    if not args.source_version or not args.target_version:
        print("ERROR: source_version and target_version required")
        return 1
    
    source = args.source_version
    target = args.target_version
    
    print(f"Migrating {source} → {target}")
    
    # Check source exists
    source_dir = CORE_DIR / source
    if not source_dir.exists():
        print(f"ERROR: Source version not found: {source_dir}")
        return 1
    
    # Check target doesn't exist (unless dry run)
    target_dir = CORE_DIR / target
    if target_dir.exists() and not args.dry_run:
        print(f"WARNING: Target version already exists: {target_dir}")
        confirm = input("Overwrite? [y/N] ")
        if confirm.lower() != "y":
            return 1
    
    # Load source registry
    print(f"Loading {source}...")
    registry = load_registry(source)
    tags = registry.get("tags", {})
    print(f"  Found {len(tags)} tags")
    
    # Update metadata
    registry["content_version"] = target.lstrip("v")
    registry["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
    
    # Apply migrations
    if args.apply_migrations or args.migration:
        migrations_to_run = args.migration or list(MIGRATIONS.keys())
        
        print()
        print("Running migrations...")
        
        for name in migrations_to_run:
            if name not in MIGRATIONS:
                print(f"  SKIP: Unknown migration '{name}'")
                continue
            
            count = run_migration(name, registry, target)
            print(f"  {name}: {count} changes")
    
    # Save
    if args.dry_run:
        print()
        print("DRY RUN - no changes saved")
        print(f"Would create: {target_dir}")
    else:
        # Copy contracts if they exist
        source_contracts = source_dir / "contracts"
        if source_contracts.exists():
            target_contracts = target_dir / "contracts"
            shutil.copytree(source_contracts, target_contracts, dirs_exist_ok=True)
            print(f"Copied contracts to {target_contracts}")
        
        # Save registry
        reg_path = save_registry(registry, target)
        print()
        print(f"Created {target_dir}")
        print(f"  Registry: {reg_path}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
