#!/usr/bin/env python3
"""
TRS-402: Batch import/export CLI for tags.

Usage:
    # Export
    python scripts/batch.py export v0.2.8 --output tags.json
    python scripts/batch.py export v0.2.8 --output tags.csv --format csv
    python scripts/batch.py export v0.2.8 --domain "A. Luminous" --output lighting.json
    
    # Import (creates proposals)
    python scripts/batch.py import tags.json --submitter researcher@lab.edu
    python scripts/batch.py import tags.csv --format csv

Formats:
    json: Full tag data as JSON array
    csv: Flat CSV with core fields only
    yaml: YAML format
"""

from __future__ import annotations
import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any, Optional

import yaml

# Add parent to path
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(REPO_ROOT))


def load_registry(version: str) -> dict:
    """Load registry for a version."""
    registry_dir = REPO_ROOT / "core" / "trs-core" / version / "registry"
    yamls = sorted(list(registry_dir.glob("*.yml")) + list(registry_dir.glob("*.yaml")))
    if not yamls:
        raise FileNotFoundError(f"No registry YAML in {registry_dir}")
    return yaml.safe_load(yamls[0].read_text(encoding="utf-8"))


def export_json(tags: list[dict], output: Path) -> None:
    """Export tags to JSON."""
    output.write_text(json.dumps(tags, indent=2, ensure_ascii=False), encoding="utf-8")


def export_csv(tags: list[dict], output: Path) -> None:
    """Export tags to CSV (flat structure)."""
    if not tags:
        output.write_text("")
        return
    
    # Define columns
    columns = [
        "tag_id", "canonical_name", "status", "value_type", "domain",
        "definition", "category", "extractability_2d", "extractability_3d",
    ]
    
    rows = []
    for tag in tags:
        row = {
            "tag_id": tag.get("tag_id", ""),
            "canonical_name": tag.get("canonical_name", ""),
            "status": tag.get("status", ""),
            "value_type": tag.get("value_type", ""),
            "domain": tag.get("domain", ""),
            "definition": tag.get("definition", ""),
            "category": tag.get("category", ""),
            "extractability_2d": tag.get("extractability", {}).get("from_2d", ""),
            "extractability_3d": tag.get("extractability", {}).get("from_3d_vr", ""),
        }
        rows.append(row)
    
    with open(output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def export_yaml(tags: list[dict], output: Path) -> None:
    """Export tags to YAML."""
    output.write_text(
        yaml.dump(tags, default_flow_style=False, allow_unicode=True),
        encoding="utf-8"
    )


def cmd_export(args):
    """Export tags from registry."""
    registry = load_registry(args.version)
    tags = registry.get("tags", {})
    
    # Filter
    if args.domain:
        tags = {k: v for k, v in tags.items() if v.get("domain") == args.domain}
    if args.status:
        tags = {k: v for k, v in tags.items() if v.get("status") == args.status}
    
    # Convert to list with tag_id
    tag_list = []
    for tag_id, tag_data in tags.items():
        tag = {"tag_id": tag_id, **tag_data}
        tag_list.append(tag)
    
    # Sort by tag_id
    tag_list.sort(key=lambda x: x["tag_id"])
    
    # Export
    output = Path(args.output)
    
    if args.format == "json":
        export_json(tag_list, output)
    elif args.format == "csv":
        export_csv(tag_list, output)
    elif args.format == "yaml":
        export_yaml(tag_list, output)
    else:
        print(f"Unknown format: {args.format}")
        return 1
    
    print(f"Exported {len(tag_list)} tags to {output}")
    return 0


def import_json(path: Path) -> list[dict]:
    """Import tags from JSON."""
    return json.loads(path.read_text(encoding="utf-8"))


def import_csv(path: Path) -> list[dict]:
    """Import tags from CSV."""
    tags = []
    with open(path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            tag = {
                "tag_id": row.get("tag_id", ""),
                "canonical_name": row.get("canonical_name", ""),
                "status": row.get("status", "active"),
                "value_type": row.get("value_type", "ordinal"),
                "domain": row.get("domain", ""),
                "definition": row.get("definition", ""),
                "category": row.get("category", "environmental"),
            }
            
            # Handle extractability
            if row.get("extractability_2d") or row.get("extractability_3d"):
                tag["extractability"] = {}
                if row.get("extractability_2d"):
                    tag["extractability"]["from_2d"] = row["extractability_2d"]
                if row.get("extractability_3d"):
                    tag["extractability"]["from_3d_vr"] = row["extractability_3d"]
            
            tags.append(tag)
    
    return tags


def import_yaml(path: Path) -> list[dict]:
    """Import tags from YAML."""
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def cmd_import(args):
    """Import tags as proposals."""
    from backend.app.db import get_db
    
    db = get_db()
    input_path = Path(args.input)
    
    # Load tags
    if args.format == "json":
        tags = import_json(input_path)
    elif args.format == "csv":
        tags = import_csv(input_path)
    elif args.format == "yaml":
        tags = import_yaml(input_path)
    else:
        print(f"Unknown format: {args.format}")
        return 1
    
    if not tags:
        print("No tags to import.")
        return 0
    
    print(f"Importing {len(tags)} tags as proposals...")
    
    created = 0
    skipped = 0
    errors = 0
    
    for tag in tags:
        tag_id = tag.get("tag_id")
        if not tag_id:
            print(f"  SKIP: Missing tag_id")
            skipped += 1
            continue
        
        # Check for existing pending proposal
        existing = db.list_proposals(status="pending")
        if any(p.tag_id == tag_id for p in existing):
            print(f"  SKIP: {tag_id} (pending proposal exists)")
            skipped += 1
            continue
        
        try:
            # Build payload (remove tag_id from payload)
            payload = {k: v for k, v in tag.items() if k != "tag_id"}
            
            proposal_id = db.create_proposal(
                proposal_type=args.proposal_type,
                tag_id=tag_id,
                canonical_name=tag.get("canonical_name"),
                payload=payload,
                submitter=args.submitter,
                reason=f"Batch import from {input_path.name}",
            )
            
            db.log_action(
                action="proposal_created",
                user_id=args.submitter,
                target_type="proposal",
                target_id=str(proposal_id),
                details={"tag_id": tag_id, "source": "batch_import"},
            )
            
            created += 1
            if not args.quiet:
                print(f"  Created: {tag_id} (#{proposal_id})")
                
        except Exception as e:
            print(f"  ERROR: {tag_id}: {e}")
            errors += 1
    
    print()
    print(f"Results: {created} created, {skipped} skipped, {errors} errors")
    return 0 if errors == 0 else 1


def main():
    parser = argparse.ArgumentParser(description="TRS Batch Import/Export")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # export
    p_export = subparsers.add_parser("export", help="Export tags from registry")
    p_export.add_argument("version", help="Registry version (e.g., v0.2.8)")
    p_export.add_argument("--output", "-o", required=True, help="Output file path")
    p_export.add_argument("--format", "-f", default="json", choices=["json", "csv", "yaml"])
    p_export.add_argument("--domain", help="Filter by domain")
    p_export.add_argument("--status", help="Filter by status")
    p_export.set_defaults(func=cmd_export)
    
    # import
    p_import = subparsers.add_parser("import", help="Import tags as proposals")
    p_import.add_argument("input", help="Input file path")
    p_import.add_argument("--format", "-f", default="json", choices=["json", "csv", "yaml"])
    p_import.add_argument("--submitter", default="batch@localhost", help="Submitter identity")
    p_import.add_argument("--proposal-type", default="new_tag", choices=["new_tag", "modify_tag"])
    p_import.add_argument("--quiet", "-q", action="store_true", help="Quiet output")
    p_import.set_defaults(func=cmd_import)
    
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
