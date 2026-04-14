#!/usr/bin/env python3
"""
TRS-301: Merge approved proposals into the registry YAML.

Usage:
    python scripts/merge_proposals.py v0.2.9
    python scripts/merge_proposals.py v0.2.9 --dry-run
    python scripts/merge_proposals.py v0.2.9 --from-db

This script:
1. Reads approved proposals from the database
2. Applies changes to the registry YAML
3. Updates proposal status to 'merged'
4. Logs all changes to audit trail

Proposal types:
- new_tag: Add new tag to registry
- modify_tag: Update existing tag fields
- deprecate_tag: Set status=deprecated, add replaced_by
"""

from __future__ import annotations
import argparse
import copy
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import yaml

# Add parent to path
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(REPO_ROOT))

from backend.app.db import get_db, Proposal


def load_registry(registry_path: Path) -> tuple[dict, Path]:
    """Load registry YAML."""
    if registry_path.is_dir():
        yamls = sorted(list(registry_path.glob("*.yml")) + list(registry_path.glob("*.yaml")))
        if not yamls:
            raise FileNotFoundError(f"No registry YAML in {registry_path}")
        reg_path = yamls[0]
    else:
        reg_path = registry_path
    
    return yaml.safe_load(reg_path.read_text(encoding="utf-8")), reg_path


def save_registry(registry: dict, path: Path, backup: bool = True) -> None:
    """Save registry YAML with optional backup."""
    if backup and path.exists():
        backup_path = path.with_suffix(f".yaml.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        backup_path.write_text(path.read_text())
        print(f"  Backup: {backup_path.name}")
    
    # Custom YAML dumper for better formatting
    yaml_content = yaml.dump(
        registry,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
        width=120,
    )
    path.write_text(yaml_content, encoding="utf-8")


def apply_new_tag(registry: dict, proposal: Proposal) -> dict:
    """Apply a new_tag proposal."""
    tags = registry.setdefault("tags", {})
    
    if proposal.tag_id in tags:
        raise ValueError(f"Tag {proposal.tag_id} already exists")
    
    # Build tag from payload
    tag_data = copy.deepcopy(proposal.payload)
    
    # Ensure required fields
    tag_data.setdefault("canonical_name", proposal.canonical_name)
    tag_data.setdefault("status", "active")
    tag_data.setdefault("version_added", registry.get("content_version", "0.0.0"))
    
    tags[proposal.tag_id] = tag_data
    return registry


def apply_modify_tag(registry: dict, proposal: Proposal) -> dict:
    """Apply a modify_tag proposal."""
    tags = registry.get("tags", {})
    
    if proposal.tag_id not in tags:
        raise ValueError(f"Tag {proposal.tag_id} does not exist")
    
    existing = tags[proposal.tag_id]
    updates = proposal.payload
    
    # Deep merge updates into existing
    def deep_merge(base: dict, updates: dict) -> dict:
        result = copy.deepcopy(base)
        for key, value in updates.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = deep_merge(result[key], value)
            else:
                result[key] = copy.deepcopy(value)
        return result
    
    tags[proposal.tag_id] = deep_merge(existing, updates)
    tags[proposal.tag_id]["version_modified"] = registry.get("content_version", "0.0.0")
    
    return registry


def apply_deprecate_tag(registry: dict, proposal: Proposal) -> dict:
    """Apply a deprecate_tag proposal."""
    tags = registry.get("tags", {})
    
    if proposal.tag_id not in tags:
        raise ValueError(f"Tag {proposal.tag_id} does not exist")
    
    tag = tags[proposal.tag_id]
    tag["status"] = "deprecated"
    tag["version_modified"] = registry.get("content_version", "0.0.0")
    
    # Add replaced_by if specified in payload
    if "replaced_by" in proposal.payload:
        tag["replaced_by"] = proposal.payload["replaced_by"]
    
    return registry


def apply_proposal(registry: dict, proposal: Proposal) -> dict:
    """Apply a single proposal to the registry."""
    if proposal.proposal_type == "new_tag":
        return apply_new_tag(registry, proposal)
    elif proposal.proposal_type == "modify_tag":
        return apply_modify_tag(registry, proposal)
    elif proposal.proposal_type == "deprecate_tag":
        return apply_deprecate_tag(registry, proposal)
    else:
        raise ValueError(f"Unknown proposal type: {proposal.proposal_type}")


def merge_proposals(
    version: str,
    registry_dir: Optional[Path] = None,
    dry_run: bool = False,
    verbose: bool = False,
) -> tuple[int, int, list[str]]:
    """
    Merge all approved proposals into the registry.
    
    Returns (merged_count, error_count, error_messages)
    """
    db = get_db()
    
    # Find registry
    if registry_dir is None:
        registry_dir = REPO_ROOT / "core" / "trs-core" / version / "registry"
    
    if not registry_dir.exists():
        raise FileNotFoundError(f"Registry not found: {registry_dir}")
    
    # Load registry
    registry, reg_path = load_registry(registry_dir)
    original_tag_count = len(registry.get("tags", {}))
    
    print(f"Merging proposals into {reg_path.name}")
    print(f"  Current tags: {original_tag_count}")
    print()
    
    # Get approved proposals
    proposals = db.list_proposals(status="approved")
    
    if not proposals:
        print("No approved proposals to merge.")
        return 0, 0, []
    
    print(f"Found {len(proposals)} approved proposals:")
    for p in proposals:
        print(f"  [{p.proposal_type}] {p.tag_id} — {p.canonical_name or 'N/A'}")
    print()
    
    # Apply each proposal
    merged = 0
    errors = 0
    error_messages = []
    
    for proposal in proposals:
        try:
            if verbose:
                print(f"Applying: {proposal.tag_id}...")
            
            registry = apply_proposal(registry, proposal)
            
            if not dry_run:
                # Update status to merged
                db.update_proposal_status(proposal.id, "merged")
                
                # Log the merge
                db.log_action(
                    action="proposal_merged",
                    user_id="merge_script",
                    target_type="proposal",
                    target_id=str(proposal.id),
                    details={"tag_id": proposal.tag_id, "type": proposal.proposal_type},
                )
            
            merged += 1
            
        except Exception as e:
            error_msg = f"Failed to apply {proposal.tag_id}: {e}"
            error_messages.append(error_msg)
            errors += 1
            print(f"  ERROR: {error_msg}")
    
    # Save registry
    new_tag_count = len(registry.get("tags", {}))
    
    if dry_run:
        print()
        print("DRY RUN — No changes written")
        print(f"  Would merge: {merged} proposals")
        print(f"  Tags before: {original_tag_count}")
        print(f"  Tags after: {new_tag_count}")
    else:
        # Update content version timestamp
        registry["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
        
        save_registry(registry, reg_path)
        
        print()
        print(f"SUCCESS: Merged {merged} proposals")
        print(f"  Tags before: {original_tag_count}")
        print(f"  Tags after: {new_tag_count}")
        print(f"  Written to: {reg_path}")
    
    if errors:
        print(f"  Errors: {errors}")
    
    return merged, errors, error_messages


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge approved proposals into registry")
    parser.add_argument("version", help="Version string (e.g., v0.2.9)")
    parser.add_argument("--registry-dir", type=Path, help="Registry directory")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be merged")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    if not args.version.startswith("v"):
        print("ERROR: Version must start with 'v'")
        return 1

    try:
        merged, errors, _ = merge_proposals(
            version=args.version,
            registry_dir=args.registry_dir,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )
        return 1 if errors > 0 else 0
    except Exception as e:
        print(f"ERROR: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
