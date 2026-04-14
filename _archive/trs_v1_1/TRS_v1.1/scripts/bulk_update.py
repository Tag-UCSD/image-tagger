#!/usr/bin/env python3
"""
TRS-902: Bulk update script for registry tags.

Apply bulk changes to tags based on patterns or rules.

Usage:
    # Set domain for all tags matching pattern
    python scripts/bulk_update.py v0.2.8 --pattern "env.ae.*" --set domain="A. Luminous"
    
    # Add field to tags missing it
    python scripts/bulk_update.py v0.2.8 --missing status --set status=active
    
    # Update definitions matching pattern
    python scripts/bulk_update.py v0.2.8 --definition-contains "operational tag" \
        --set-definition "No definition available yet."
    
    # Dry run
    python scripts/bulk_update.py v0.2.8 --pattern "test.*" --set status=deprecated --dry-run
"""

from __future__ import annotations
import argparse
import copy
import fnmatch
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent


def load_registry(version: str) -> tuple[dict, Path]:
    """Load registry for a version."""
    registry_dir = REPO_ROOT / "core" / "trs-core" / version / "registry"
    yamls = sorted(list(registry_dir.glob("*.yml")) + list(registry_dir.glob("*.yaml")))
    if not yamls:
        raise FileNotFoundError(f"No registry YAML in {registry_dir}")
    reg_path = yamls[0]
    return yaml.safe_load(reg_path.read_text(encoding="utf-8")), reg_path


def save_registry(registry: dict, path: Path, backup: bool = True) -> None:
    """Save registry with optional backup."""
    if backup and path.exists():
        backup_path = path.with_suffix(f".yaml.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        backup_path.write_text(path.read_text())
        print(f"  Backup: {backup_path.name}")
    
    yaml_content = yaml.dump(
        registry,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
        width=120,
    )
    path.write_text(yaml_content, encoding="utf-8")


def parse_set_arg(set_arg: str) -> tuple[str, str]:
    """Parse a --set argument like 'field=value'."""
    if "=" not in set_arg:
        raise ValueError(f"Invalid --set format: {set_arg} (expected field=value)")
    field, value = set_arg.split("=", 1)
    return field.strip(), value.strip()


def set_nested_value(obj: dict, path: str, value: str) -> None:
    """Set a nested value using dot notation."""
    parts = path.split(".")
    
    for part in parts[:-1]:
        if part not in obj:
            obj[part] = {}
        obj = obj[part]
    
    # Try to parse value as JSON for complex types
    try:
        parsed = json.loads(value)
        obj[parts[-1]] = parsed
    except json.JSONDecodeError:
        # Use as string
        obj[parts[-1]] = value


def match_tag(tag_id: str, tag: dict, args) -> bool:
    """Check if tag matches the filter criteria."""
    # Pattern match on tag_id
    if args.pattern:
        if not fnmatch.fnmatch(tag_id, args.pattern):
            return False
    
    # Missing field
    if args.missing:
        if tag.get(args.missing):
            return False
    
    # Has field with value
    if args.has_field:
        field, expected = parse_set_arg(args.has_field)
        if str(tag.get(field)) != expected:
            return False
    
    # Definition contains
    if args.definition_contains:
        definition = tag.get("definition", "")
        if args.definition_contains.lower() not in definition.lower():
            return False
    
    # Domain filter
    if args.domain:
        if tag.get("domain") != args.domain:
            return False
    
    # Status filter
    if args.status:
        if tag.get("status") != args.status:
            return False
    
    return True


def apply_updates(tag: dict, args) -> dict:
    """Apply updates to a tag."""
    updated = copy.deepcopy(tag)
    
    # Apply --set arguments
    for set_arg in args.set or []:
        field, value = parse_set_arg(set_arg)
        set_nested_value(updated, field, value)
    
    # Apply definition update
    if args.set_definition:
        updated["definition"] = args.set_definition
    
    # Delete field
    if args.delete_field:
        if args.delete_field in updated:
            del updated[args.delete_field]
    
    # Add version_modified
    if updated != tag:
        updated["version_modified"] = args.version
    
    return updated


def main():
    parser = argparse.ArgumentParser(description="Bulk update registry tags")
    parser.add_argument("version", help="Registry version (e.g., v0.2.8)")
    parser.add_argument("--dry-run", action="store_true", help="Don't save changes")
    parser.add_argument("--no-backup", action="store_true", help="Skip backup")
    
    # Filters
    filter_group = parser.add_argument_group("Filters")
    filter_group.add_argument("--pattern", help="Tag ID pattern (e.g., 'env.ae.*')")
    filter_group.add_argument("--missing", help="Tags missing this field")
    filter_group.add_argument("--has-field", help="Tags with field=value")
    filter_group.add_argument("--definition-contains", help="Definition contains text")
    filter_group.add_argument("--domain", help="Filter by domain")
    filter_group.add_argument("--status", help="Filter by status")
    
    # Updates
    update_group = parser.add_argument_group("Updates")
    update_group.add_argument("--set", action="append", help="Set field=value")
    update_group.add_argument("--set-definition", help="Set definition text")
    update_group.add_argument("--delete-field", help="Delete field from tags")
    
    args = parser.parse_args()
    
    if not args.set and not args.set_definition and not args.delete_field:
        print("ERROR: No update specified. Use --set, --set-definition, or --delete-field")
        return 1
    
    print(f"Loading {args.version}...")
    registry, reg_path = load_registry(args.version)
    tags = registry.get("tags", {})
    print(f"  Found {len(tags)} tags")
    
    # Find matching tags
    matching = []
    for tag_id, tag in tags.items():
        if not isinstance(tag, dict):
            continue
        if match_tag(tag_id, tag, args):
            matching.append(tag_id)
    
    print(f"  {len(matching)} tags match filters")
    
    if not matching:
        print("No tags to update.")
        return 0
    
    # Preview
    print()
    print("Tags to update:")
    for tag_id in matching[:10]:
        print(f"  {tag_id}")
    if len(matching) > 10:
        print(f"  ... and {len(matching) - 10} more")
    
    print()
    print("Updates to apply:")
    for set_arg in args.set or []:
        print(f"  SET {set_arg}")
    if args.set_definition:
        print(f"  SET definition = {args.set_definition[:50]}...")
    if args.delete_field:
        print(f"  DELETE {args.delete_field}")
    
    if args.dry_run:
        print()
        print("DRY RUN - no changes saved")
        return 0
    
    # Apply updates
    print()
    print("Applying updates...")
    
    updated_count = 0
    for tag_id in matching:
        original = tags[tag_id]
        updated = apply_updates(original, args)
        
        if updated != original:
            tags[tag_id] = updated
            updated_count += 1
    
    # Save
    save_registry(registry, reg_path, backup=not args.no_backup)
    
    print(f"Updated {updated_count} tags")
    print(f"Saved to {reg_path}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
