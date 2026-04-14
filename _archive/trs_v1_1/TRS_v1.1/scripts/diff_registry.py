#!/usr/bin/env python3
"""
TRS-104: Detect breaking changes between registry versions.

Usage:
    python scripts/diff_registry.py v0.2.7 v0.2.8
    python scripts/diff_registry.py core/trs-core/v0.2.7/registry/ core/trs-core/v0.2.8/registry/
    python scripts/diff_registry.py v0.2.7 v0.2.8 --json

Change Classification:
    BREAKING: Will break clients (removed tags, type changes, ID renames)
    WARNING: May affect clients (extractability downgrades, deprecations)
    INFO: Safe changes (new tags, added aliases, updated definitions)

Exit codes:
    0 = No breaking changes
    1 = Breaking changes detected
    2 = Failed to load registries
"""

from __future__ import annotations
import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class Change:
    """A single change between versions."""
    severity: str  # BREAKING, WARNING, INFO
    change_type: str
    tag_id: str
    details: str
    old_value: Any = None
    new_value: Any = None

    def __str__(self):
        return f"[{self.severity}] {self.change_type}: {self.tag_id} - {self.details}"


@dataclass
class DiffResult:
    """Collection of changes between versions."""
    old_version: str
    new_version: str
    changes: list[Change] = field(default_factory=list)
    
    @property
    def breaking_changes(self) -> list[Change]:
        return [c for c in self.changes if c.severity == "BREAKING"]
    
    @property
    def warnings(self) -> list[Change]:
        return [c for c in self.changes if c.severity == "WARNING"]
    
    @property
    def info(self) -> list[Change]:
        return [c for c in self.changes if c.severity == "INFO"]
    
    @property
    def has_breaking(self) -> bool:
        return len(self.breaking_changes) > 0
    
    def to_dict(self) -> dict:
        return {
            "old_version": self.old_version,
            "new_version": self.new_version,
            "has_breaking_changes": self.has_breaking,
            "summary": {
                "breaking": len(self.breaking_changes),
                "warning": len(self.warnings),
                "info": len(self.info),
            },
            "changes": [
                {
                    "severity": c.severity,
                    "type": c.change_type,
                    "tag_id": c.tag_id,
                    "details": c.details,
                    "old_value": c.old_value,
                    "new_value": c.new_value,
                }
                for c in self.changes
            ],
        }


def load_registry(registry_path: Path) -> tuple[dict, str]:
    """Load registry from path (directory or version string)."""
    # If it's a version string like v0.2.8, resolve to directory
    if registry_path.name.startswith("v") and not registry_path.exists():
        # Try to find in standard location
        script_dir = Path(__file__).resolve().parent
        repo_root = script_dir.parent
        resolved = repo_root / "core" / "trs-core" / registry_path.name / "registry"
        if resolved.exists():
            registry_path = resolved
    
    if registry_path.is_file():
        reg_file = registry_path
    else:
        yamls = sorted(list(registry_path.glob("*.yml")) + list(registry_path.glob("*.yaml")))
        if not yamls:
            raise FileNotFoundError(f"No registry YAML found in {registry_path}")
        reg_file = yamls[0]
    
    registry = yaml.safe_load(reg_file.read_text(encoding="utf-8"))
    version = registry.get("content_version") or registry_path.parent.name if registry_path.is_file() else registry_path.name
    
    return registry, str(version)


def diff_registries(old_path: Path, new_path: Path) -> DiffResult:
    """Compare two registries and detect changes."""
    old_reg, old_ver = load_registry(old_path)
    new_reg, new_ver = load_registry(new_path)
    
    result = DiffResult(old_version=old_ver, new_version=new_ver)
    
    old_tags = old_reg.get("tags", {})
    new_tags = new_reg.get("tags", {})
    
    old_ids = set(old_tags.keys())
    new_ids = set(new_tags.keys())
    
    # Removed tags (BREAKING)
    for tag_id in old_ids - new_ids:
        result.changes.append(Change(
            severity="BREAKING",
            change_type="TAG_REMOVED",
            tag_id=tag_id,
            details="Tag was removed from registry",
        ))
    
    # Added tags (INFO)
    for tag_id in new_ids - old_ids:
        result.changes.append(Change(
            severity="INFO",
            change_type="TAG_ADDED",
            tag_id=tag_id,
            details=f"New tag: {new_tags[tag_id].get('canonical_name', 'unnamed')}",
        ))
    
    # Modified tags
    for tag_id in old_ids & new_ids:
        old_tag = old_tags[tag_id]
        new_tag = new_tags[tag_id]
        
        # value_type change (BREAKING)
        old_vt = old_tag.get("value_type")
        new_vt = new_tag.get("value_type")
        if old_vt != new_vt:
            result.changes.append(Change(
                severity="BREAKING",
                change_type="VALUE_TYPE_CHANGED",
                tag_id=tag_id,
                details=f"value_type changed from '{old_vt}' to '{new_vt}'",
                old_value=old_vt,
                new_value=new_vt,
            ))
        
        # Status change to deprecated (WARNING)
        old_status = old_tag.get("status")
        new_status = new_tag.get("status")
        if old_status != "deprecated" and new_status == "deprecated":
            result.changes.append(Change(
                severity="WARNING",
                change_type="TAG_DEPRECATED",
                tag_id=tag_id,
                details=f"Tag deprecated (was '{old_status}')",
                old_value=old_status,
                new_value=new_status,
            ))
        
        # Extractability downgrade (WARNING)
        old_extract = old_tag.get("extractability", {}).get("from_2d")
        new_extract = new_tag.get("extractability", {}).get("from_2d")
        extract_order = {"yes": 3, "partial": 2, "no": 1, None: 0}
        if extract_order.get(old_extract, 0) > extract_order.get(new_extract, 0):
            result.changes.append(Change(
                severity="WARNING",
                change_type="EXTRACTABILITY_DOWNGRADE",
                tag_id=tag_id,
                details=f"from_2d downgraded from '{old_extract}' to '{new_extract}'",
                old_value=old_extract,
                new_value=new_extract,
            ))
        
        # Definition changed (INFO)
        old_def = old_tag.get("definition")
        new_def = new_tag.get("definition")
        if old_def != new_def and old_def and new_def:
            result.changes.append(Change(
                severity="INFO",
                change_type="DEFINITION_CHANGED",
                tag_id=tag_id,
                details="Definition was updated",
            ))
        
        # Aliases added (INFO)
        old_aliases = set(old_tag.get("semantics", {}).get("aliases", []))
        new_aliases = set(new_tag.get("semantics", {}).get("aliases", []))
        added_aliases = new_aliases - old_aliases
        if added_aliases:
            result.changes.append(Change(
                severity="INFO",
                change_type="ALIASES_ADDED",
                tag_id=tag_id,
                details=f"Added aliases: {', '.join(sorted(added_aliases))}",
            ))
    
    # Sort changes by severity
    severity_order = {"BREAKING": 0, "WARNING": 1, "INFO": 2}
    result.changes.sort(key=lambda c: (severity_order[c.severity], c.tag_id))
    
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Detect breaking changes between registry versions")
    parser.add_argument("old_version", type=Path, help="Old version (e.g., v0.2.7 or path to registry)")
    parser.add_argument("new_version", type=Path, help="New version (e.g., v0.2.8 or path to registry)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--breaking-only", action="store_true", help="Only show breaking changes")
    args = parser.parse_args()

    try:
        result = diff_registries(args.old_version, args.new_version)
    except Exception as e:
        print(f"ERROR: {e}")
        return 2

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(f"Comparing {result.old_version} → {result.new_version}")
        print()
        
        if result.breaking_changes:
            print(f"=== BREAKING CHANGES ({len(result.breaking_changes)}) ===")
            for change in result.breaking_changes:
                print(f"  {change}")
            print()
        
        if result.warnings and not args.breaking_only:
            print(f"=== WARNINGS ({len(result.warnings)}) ===")
            for change in result.warnings:
                print(f"  {change}")
            print()
        
        if result.info and not args.breaking_only:
            print(f"=== INFO ({len(result.info)}) ===")
            for change in result.info[:20]:  # Limit info output
                print(f"  {change}")
            if len(result.info) > 20:
                print(f"  ... and {len(result.info) - 20} more")
            print()
        
        # Summary
        print("=" * 50)
        print(f"Summary: {len(result.breaking_changes)} breaking, {len(result.warnings)} warnings, {len(result.info)} info")
        
        if result.has_breaking:
            print()
            print("❌ BREAKING CHANGES DETECTED - Release blocked")
        else:
            print()
            print("✓ No breaking changes - Safe to release")

    return 1 if result.has_breaking else 0


if __name__ == "__main__":
    sys.exit(main())
