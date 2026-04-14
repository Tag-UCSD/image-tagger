#!/usr/bin/env python3
"""
TRS-502: Generate changelog between registry versions.

Usage:
    python scripts/changelog.py v0.2.7 v0.2.8
    python scripts/changelog.py v0.2.7 v0.2.8 --output CHANGELOG.md
    python scripts/changelog.py v0.2.7 v0.2.8 --format json

Generates a human-readable changelog showing:
- Added tags
- Modified tags (with field-level diffs)
- Deprecated tags
- Removed tags (if any)
"""

from __future__ import annotations
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import yaml

# Add parent to path
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent


def load_registry(version: str) -> dict:
    """Load registry for a version."""
    registry_dir = REPO_ROOT / "core" / "trs-core" / version / "registry"
    yamls = sorted(list(registry_dir.glob("*.yml")) + list(registry_dir.glob("*.yaml")))
    if not yamls:
        raise FileNotFoundError(f"No registry YAML in {registry_dir}")
    return yaml.safe_load(yamls[0].read_text(encoding="utf-8"))


def diff_tag(old_tag: dict, new_tag: dict) -> list[tuple[str, str, str]]:
    """
    Compare two tags and return list of changes.
    Returns list of (field, old_value, new_value) tuples.
    """
    changes = []
    
    # Fields to compare
    fields = [
        "canonical_name", "status", "value_type", "definition", "domain",
        "category", "version_added", "version_modified",
    ]
    
    for field in fields:
        old_val = old_tag.get(field)
        new_val = new_tag.get(field)
        if old_val != new_val:
            changes.append((field, str(old_val), str(new_val)))
    
    # Compare extractability
    old_extract = old_tag.get("extractability", {})
    new_extract = new_tag.get("extractability", {})
    for key in ["from_2d", "from_3d_vr", "monocular_3d_approx"]:
        old_val = old_extract.get(key)
        new_val = new_extract.get(key)
        if old_val != new_val:
            changes.append((f"extractability.{key}", str(old_val), str(new_val)))
    
    # Compare aliases
    old_aliases = set(old_tag.get("semantics", {}).get("aliases", []))
    new_aliases = set(new_tag.get("semantics", {}).get("aliases", []))
    added_aliases = new_aliases - old_aliases
    removed_aliases = old_aliases - new_aliases
    
    if added_aliases:
        changes.append(("aliases_added", "", ", ".join(sorted(added_aliases))))
    if removed_aliases:
        changes.append(("aliases_removed", ", ".join(sorted(removed_aliases)), ""))
    
    return changes


def generate_changelog(old_version: str, new_version: str) -> dict:
    """Generate changelog between two versions."""
    old_registry = load_registry(old_version)
    new_registry = load_registry(new_version)
    
    old_tags = old_registry.get("tags", {})
    new_tags = new_registry.get("tags", {})
    
    old_ids = set(old_tags.keys())
    new_ids = set(new_tags.keys())
    
    # Categorize changes
    added = []
    removed = []
    modified = []
    deprecated = []
    
    # Added tags
    for tag_id in sorted(new_ids - old_ids):
        tag = new_tags[tag_id]
        added.append({
            "tag_id": tag_id,
            "canonical_name": tag.get("canonical_name"),
            "domain": tag.get("domain"),
            "value_type": tag.get("value_type"),
        })
    
    # Removed tags
    for tag_id in sorted(old_ids - new_ids):
        tag = old_tags[tag_id]
        removed.append({
            "tag_id": tag_id,
            "canonical_name": tag.get("canonical_name"),
        })
    
    # Modified tags
    for tag_id in sorted(old_ids & new_ids):
        old_tag = old_tags[tag_id]
        new_tag = new_tags[tag_id]
        
        changes = diff_tag(old_tag, new_tag)
        
        if changes:
            # Check if newly deprecated
            old_status = old_tag.get("status")
            new_status = new_tag.get("status")
            
            if old_status != "deprecated" and new_status == "deprecated":
                deprecated.append({
                    "tag_id": tag_id,
                    "canonical_name": new_tag.get("canonical_name"),
                    "replaced_by": new_tag.get("replaced_by"),
                })
            else:
                modified.append({
                    "tag_id": tag_id,
                    "canonical_name": new_tag.get("canonical_name"),
                    "changes": [
                        {"field": f, "old": o, "new": n}
                        for f, o, n in changes
                    ],
                })
    
    return {
        "old_version": old_version,
        "new_version": new_version,
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "added": len(added),
            "modified": len(modified),
            "deprecated": len(deprecated),
            "removed": len(removed),
        },
        "added": added,
        "modified": modified,
        "deprecated": deprecated,
        "removed": removed,
    }


def format_markdown(changelog: dict) -> str:
    """Format changelog as Markdown."""
    lines = [
        f"# Changelog: {changelog['old_version']} → {changelog['new_version']}",
        f"",
        f"Generated: {changelog['generated_at'][:10]}",
        f"",
        f"## Summary",
        f"",
        f"| Change Type | Count |",
        f"|-------------|-------|",
        f"| Added | {changelog['summary']['added']} |",
        f"| Modified | {changelog['summary']['modified']} |",
        f"| Deprecated | {changelog['summary']['deprecated']} |",
        f"| Removed | {changelog['summary']['removed']} |",
        f"",
    ]
    
    # Added
    if changelog["added"]:
        lines.append(f"## ➕ Added Tags ({len(changelog['added'])})")
        lines.append(f"")
        for tag in changelog["added"]:
            lines.append(f"### {tag['canonical_name']}")
            lines.append(f"")
            lines.append(f"- **Tag ID:** `{tag['tag_id']}`")
            lines.append(f"- **Domain:** {tag.get('domain', 'N/A')}")
            lines.append(f"- **Type:** {tag.get('value_type', 'N/A')}")
            lines.append(f"")
    
    # Modified
    if changelog["modified"]:
        lines.append(f"## ✏️ Modified Tags ({len(changelog['modified'])})")
        lines.append(f"")
        for tag in changelog["modified"]:
            lines.append(f"### {tag['canonical_name']}")
            lines.append(f"")
            lines.append(f"**Tag ID:** `{tag['tag_id']}`")
            lines.append(f"")
            lines.append(f"| Field | Old | New |")
            lines.append(f"|-------|-----|-----|")
            for change in tag["changes"]:
                old = change["old"][:30] + "..." if len(change["old"]) > 30 else change["old"]
                new = change["new"][:30] + "..." if len(change["new"]) > 30 else change["new"]
                lines.append(f"| {change['field']} | {old} | {new} |")
            lines.append(f"")
    
    # Deprecated
    if changelog["deprecated"]:
        lines.append(f"## ⚠️ Deprecated Tags ({len(changelog['deprecated'])})")
        lines.append(f"")
        for tag in changelog["deprecated"]:
            replaced = tag.get("replaced_by")
            if replaced:
                lines.append(f"- **{tag['tag_id']}** → `{replaced}`")
            else:
                lines.append(f"- **{tag['tag_id']}**")
        lines.append(f"")
    
    # Removed
    if changelog["removed"]:
        lines.append(f"## ❌ Removed Tags ({len(changelog['removed'])})")
        lines.append(f"")
        lines.append(f"⚠️ **Breaking Change**: The following tags were removed.")
        lines.append(f"")
        for tag in changelog["removed"]:
            lines.append(f"- `{tag['tag_id']}` ({tag.get('canonical_name', 'N/A')})")
        lines.append(f"")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate changelog between versions")
    parser.add_argument("old_version", help="Old version (e.g., v0.2.7)")
    parser.add_argument("new_version", help="New version (e.g., v0.2.8)")
    parser.add_argument("--output", "-o", help="Output file")
    parser.add_argument("--format", "-f", default="markdown", choices=["markdown", "json"])
    args = parser.parse_args()

    print(f"Comparing {args.old_version} → {args.new_version}...")
    
    try:
        changelog = generate_changelog(args.old_version, args.new_version)
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        return 1
    
    # Format output
    if args.format == "json":
        output = json.dumps(changelog, indent=2)
    else:
        output = format_markdown(changelog)
    
    # Write or print
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"Changelog written to {args.output}")
    else:
        print()
        print(output)
    
    # Summary
    s = changelog["summary"]
    print()
    print(f"Changes: +{s['added']} ~{s['modified']} ⚠{s['deprecated']} -{s['removed']}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
