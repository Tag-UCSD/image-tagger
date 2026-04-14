#!/usr/bin/env python3
"""
TRS-101: Generate consumer contracts from the canonical registry.

Usage:
    python scripts/generate_contracts.py v0.2.9
    python scripts/generate_contracts.py v0.2.9 --output-dir ./generated
    python scripts/generate_contracts.py v0.2.9 --dry-run

Each consumer gets a projection of the registry with fields relevant to their use case:
- image_tagger: extractability, extraction methods
- article_eater: search_terms, aliases for literature mining
- bn: Bayesian network fields (demand_state, evidence_role, etc.)
- preference_testing: value_type, definition for survey design
"""

from __future__ import annotations
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


def sha256_file(path: Path) -> str:
    """Compute SHA256 hash of a file."""
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def load_registry(registry_dir: Path) -> tuple[dict, Path]:
    """Load registry YAML and return (data, path)."""
    yamls = sorted(list(registry_dir.glob("*.yml")) + list(registry_dir.glob("*.yaml")))
    if not yamls:
        raise FileNotFoundError(f"No registry YAML found in {registry_dir}")
    reg_path = yamls[0]
    return yaml.safe_load(reg_path.read_text(encoding="utf-8")), reg_path


def generate_meta(registry_sha256: str, version: str) -> dict:
    """Generate contract metadata."""
    return {
        "registry_sha256": registry_sha256,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "contract_version": version,
    }


def generate_image_tagger_contract(tags: dict, meta: dict, version: str) -> dict:
    """
    Image Tagger contract: extraction-focused fields.
    Includes all tags with extractability and extraction info.
    """
    contract_tags = []
    for tag_id, tag in tags.items():
        contract_tags.append({
            "tag_id": tag_id,
            "value_type": tag.get("value_type"),
            "extractability": tag.get("extractability", {}),
            "extraction": tag.get("extraction", {}),
        })
    
    return {
        "meta": meta,
        "contract_version": version,
        "tags": contract_tags,
    }


def generate_article_eater_contract(tags: dict, meta: dict, version: str, source_registry: dict) -> dict:
    """
    Article Eater contract: search and alias fields for literature mining.
    """
    contract_tags = []
    for tag_id, tag in tags.items():
        # Get search terms from literature section
        literature = tag.get("literature", {})
        search_terms = literature.get("search_terms", [])
        if not search_terms and tag.get("canonical_name"):
            search_terms = [tag.get("canonical_name")]
        
        # Get aliases from semantics
        semantics = tag.get("semantics", {})
        aliases = semantics.get("aliases", [])
        
        contract_tags.append({
            "tag_id": tag_id,
            "status": tag.get("status"),
            "search_terms": search_terms,
            "aliases": aliases,
        })
    
    return {
        "meta": meta,
        "contract_version": version,
        "source_registry": {
            "content_version": source_registry.get("content_version"),
            "generated_at_utc": source_registry.get("generated_at_utc"),
        },
        "tags": contract_tags,
    }


def generate_bn_contract(tags: dict, meta: dict, version: str) -> dict:
    """
    Bayesian Network contract: BN-specific fields.
    """
    contract_tags = []
    for tag_id, tag in tags.items():
        bn = tag.get("bn", {})
        contract_tags.append({
            "tag_id": tag_id,
            "bn": {
                "demand_state": bn.get("demand_state"),
                "evidence_role": bn.get("evidence_role"),
                "consumable": bn.get("consumable"),
                "parent_tags": bn.get("parent_tags"),
                "child_tags": bn.get("child_tags"),
            },
        })
    
    return {
        "meta": meta,
        "contract_version": version,
        "tags": contract_tags,
    }


def generate_preference_testing_contract(tags: dict, meta: dict, version: str) -> dict:
    """
    Preference Testing contract: value_type and definition for survey design.
    """
    contract_tags = []
    for tag_id, tag in tags.items():
        contract_tags.append({
            "tag_id": tag_id,
            "value_type": tag.get("value_type"),
            "definition": tag.get("definition"),
        })
    
    return {
        "meta": meta,
        "contract_version": version,
        "tags": contract_tags,
    }


def write_contract(contract: dict, path: Path, dry_run: bool = False) -> None:
    """Write contract JSON with consistent formatting."""
    content = json.dumps(contract, indent=2, ensure_ascii=False)
    if dry_run:
        print(f"  Would write: {path} ({len(content)} bytes)")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(f"  Wrote: {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate consumer contracts from registry")
    parser.add_argument("version", help="Version string (e.g., v0.2.9)")
    parser.add_argument("--registry-dir", type=Path, 
                        help="Registry directory (default: auto-detect from version)")
    parser.add_argument("--output-dir", type=Path,
                        help="Output directory (default: alongside registry)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be generated without writing")
    args = parser.parse_args()

    # Validate version format
    if not args.version.startswith("v"):
        print(f"ERROR: Version must start with 'v' (got: {args.version})")
        return 1

    # Find repo root
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    
    # Determine registry directory
    if args.registry_dir:
        registry_dir = args.registry_dir
    else:
        registry_dir = repo_root / "core" / "trs-core" / args.version / "registry"
    
    if not registry_dir.exists():
        print(f"ERROR: Registry directory not found: {registry_dir}")
        return 1

    # Determine output directory
    if args.output_dir:
        output_dir = args.output_dir
    else:
        output_dir = registry_dir.parent / "contracts"

    print(f"Generating contracts for {args.version}")
    print(f"  Registry: {registry_dir}")
    print(f"  Output: {output_dir}")
    print()

    # Load registry
    try:
        registry, reg_path = load_registry(registry_dir)
    except Exception as e:
        print(f"ERROR: Failed to load registry: {e}")
        return 1

    tags = registry.get("tags", {})
    if not tags:
        print("ERROR: No tags found in registry")
        return 1

    print(f"  Loaded {len(tags)} tags from {reg_path.name}")

    # Compute SHA256
    registry_sha256 = sha256_file(reg_path)
    print(f"  Registry SHA256: {registry_sha256[:16]}...")
    print()

    # Generate metadata
    meta = generate_meta(registry_sha256, args.version)

    # Generate contracts
    contracts = [
        ("image_tagger", generate_image_tagger_contract(tags, meta, args.version)),
        ("article_eater", generate_article_eater_contract(tags, meta, args.version, registry)),
        ("bn", generate_bn_contract(tags, meta, args.version)),
        ("preference_testing", generate_preference_testing_contract(tags, meta, args.version)),
    ]

    print("Generating contracts:")
    for name, contract in contracts:
        filename = f"{name}_contract_{args.version}.json"
        path = output_dir / filename
        write_contract(contract, path, dry_run=args.dry_run)

    # Write SHA256 manifest
    sha_manifest = {"registry_sha256": registry_sha256}
    sha_path = output_dir / f"registry_sha256_{args.version}.json"
    if args.dry_run:
        print(f"  Would write: {sha_path}")
    else:
        sha_path.parent.mkdir(parents=True, exist_ok=True)
        sha_path.write_text(json.dumps(sha_manifest, indent=2), encoding="utf-8")
        print(f"  Wrote: {sha_path}")

    print()
    print(f"SUCCESS: Generated {len(contracts)} contracts + SHA256 manifest")
    return 0


if __name__ == "__main__":
    sys.exit(main())
