#!/usr/bin/env python3
"""
TRS-406: Auto-generate documentation from the tag registry.

Usage:
    python scripts/generate_docs.py v0.2.8
    python scripts/generate_docs.py v0.2.8 --output docs/tags/
    python scripts/generate_docs.py v0.2.8 --format html

Generates:
    - INDEX.md: Complete tag listing by domain
    - Per-domain files: Detailed tag documentation
    - stats.json: Machine-readable statistics
"""

from __future__ import annotations
import argparse
import json
import sys
from collections import defaultdict
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


def generate_index(tags: dict, version: str) -> str:
    """Generate the main index document."""
    # Group by domain
    by_domain = defaultdict(list)
    for tag_id, tag in tags.items():
        domain = tag.get("domain", "Uncategorized")
        by_domain[domain].append((tag_id, tag))
    
    # Sort within each domain
    for domain in by_domain:
        by_domain[domain].sort(key=lambda x: x[0])
    
    lines = [
        f"# Tag Registry Documentation",
        f"",
        f"**Version:** {version}",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Total Tags:** {len(tags)}",
        f"",
        f"---",
        f"",
        f"## Summary by Status",
        f"",
    ]
    
    # Status counts
    status_counts = defaultdict(int)
    for tag in tags.values():
        status_counts[tag.get("status", "unknown")] += 1
    
    for status, count in sorted(status_counts.items()):
        lines.append(f"- **{status}**: {count}")
    
    lines.extend([
        f"",
        f"---",
        f"",
        f"## Tags by Domain",
        f"",
    ])
    
    # Table of contents
    for domain in sorted(by_domain.keys()):
        count = len(by_domain[domain])
        domain_slug = domain.replace(" ", "_").replace(".", "").lower()
        lines.append(f"- [{domain}](#{domain_slug}) ({count} tags)")
    
    lines.extend([f"", f"---", f""])
    
    # Domain sections
    for domain in sorted(by_domain.keys()):
        domain_slug = domain.replace(" ", "_").replace(".", "").lower()
        lines.append(f"## {domain}")
        lines.append(f"")
        
        for tag_id, tag in by_domain[domain]:
            name = tag.get("canonical_name", tag_id)
            status = tag.get("status", "unknown")
            vtype = tag.get("value_type", "unknown")
            definition = tag.get("definition", "No definition available.")
            
            # Truncate long definitions
            if len(definition) > 200:
                definition = definition[:200] + "..."
            
            status_badge = {
                "active": "🟢",
                "deprecated": "🔴",
                "experimental": "🟡",
                "proposed": "⚪",
            }.get(status, "⚪")
            
            lines.append(f"### {status_badge} {name}")
            lines.append(f"")
            lines.append(f"**Tag ID:** `{tag_id}`")
            lines.append(f"")
            lines.append(f"**Status:** {status} | **Type:** {vtype}")
            lines.append(f"")
            lines.append(f"> {definition}")
            lines.append(f"")
            
            # Extractability
            extract = tag.get("extractability", {})
            if extract:
                from_2d = extract.get("from_2d", "N/A")
                from_3d = extract.get("from_3d_vr", "N/A")
                lines.append(f"**Extractability:** 2D={from_2d}, 3D/VR={from_3d}")
                lines.append(f"")
            
            # Aliases
            semantics = tag.get("semantics", {})
            aliases = semantics.get("aliases", [])
            if aliases:
                lines.append(f"**Aliases:** {', '.join(aliases[:5])}")
                if len(aliases) > 5:
                    lines.append(f" (+{len(aliases) - 5} more)")
                lines.append(f"")
            
            lines.append(f"---")
            lines.append(f"")
    
    return "\n".join(lines)


def generate_domain_doc(domain: str, tags: list[tuple[str, dict]]) -> str:
    """Generate documentation for a single domain."""
    lines = [
        f"# {domain}",
        f"",
        f"**Tags in this domain:** {len(tags)}",
        f"",
        f"---",
        f"",
    ]
    
    for tag_id, tag in tags:
        name = tag.get("canonical_name", tag_id)
        status = tag.get("status", "unknown")
        vtype = tag.get("value_type", "unknown")
        definition = tag.get("definition", "No definition available.")
        
        lines.append(f"## {name}")
        lines.append(f"")
        lines.append(f"| Property | Value |")
        lines.append(f"|----------|-------|")
        lines.append(f"| **Tag ID** | `{tag_id}` |")
        lines.append(f"| **Status** | {status} |")
        lines.append(f"| **Value Type** | {vtype} |")
        lines.append(f"| **Category** | {tag.get('category', 'N/A')} |")
        lines.append(f"")
        lines.append(f"### Definition")
        lines.append(f"")
        lines.append(f"{definition}")
        lines.append(f"")
        
        # Extractability
        extract = tag.get("extractability", {})
        if extract:
            lines.append(f"### Extractability")
            lines.append(f"")
            lines.append(f"| Source | Available |")
            lines.append(f"|--------|-----------|")
            lines.append(f"| 2D Images | {extract.get('from_2d', 'N/A')} |")
            lines.append(f"| 3D/VR | {extract.get('from_3d_vr', 'N/A')} |")
            lines.append(f"| Monocular 3D | {extract.get('monocular_3d_approx', 'N/A')} |")
            lines.append(f"")
        
        # Aliases
        semantics = tag.get("semantics", {})
        aliases = semantics.get("aliases", [])
        if aliases:
            lines.append(f"### Aliases")
            lines.append(f"")
            for alias in aliases:
                lines.append(f"- {alias}")
            lines.append(f"")
        
        # BN info
        bn = tag.get("bn", {})
        if bn and any(bn.values()):
            lines.append(f"### Bayesian Network Properties")
            lines.append(f"")
            lines.append(f"| Property | Value |")
            lines.append(f"|----------|-------|")
            if bn.get("demand_state"):
                lines.append(f"| Demand State | {bn['demand_state']} |")
            if bn.get("evidence_role"):
                lines.append(f"| Evidence Role | {bn['evidence_role']} |")
            if bn.get("consumable") is not None:
                lines.append(f"| Consumable | {bn['consumable']} |")
            lines.append(f"")
        
        lines.append(f"---")
        lines.append(f"")
    
    return "\n".join(lines)


def generate_stats(tags: dict, version: str) -> dict:
    """Generate machine-readable statistics."""
    status_counts = defaultdict(int)
    type_counts = defaultdict(int)
    domain_counts = defaultdict(int)
    
    extractable_2d = 0
    extractable_3d = 0
    
    for tag in tags.values():
        status_counts[tag.get("status", "unknown")] += 1
        type_counts[tag.get("value_type", "unknown")] += 1
        domain_counts[tag.get("domain", "Uncategorized")] += 1
        
        extract = tag.get("extractability", {})
        if extract.get("from_2d") == "yes":
            extractable_2d += 1
        if extract.get("from_3d_vr") == "yes":
            extractable_3d += 1
    
    return {
        "version": version,
        "generated_at": datetime.now().isoformat(),
        "total_tags": len(tags),
        "extractable_from_2d": extractable_2d,
        "extractable_from_3d": extractable_3d,
        "by_status": dict(status_counts),
        "by_value_type": dict(type_counts),
        "by_domain": dict(domain_counts),
    }


def main():
    parser = argparse.ArgumentParser(description="Generate tag documentation")
    parser.add_argument("version", help="Registry version (e.g., v0.2.8)")
    parser.add_argument("--output", "-o", default="docs/tags", help="Output directory")
    parser.add_argument("--format", "-f", default="markdown", choices=["markdown", "html"])
    args = parser.parse_args()

    # Load registry
    print(f"Loading registry {args.version}...")
    registry = load_registry(args.version)
    tags = registry.get("tags", {})
    
    if not tags:
        print("No tags found!")
        return 1
    
    print(f"  Found {len(tags)} tags")
    
    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate index
    print("Generating index...")
    index_content = generate_index(tags, args.version)
    (output_dir / "INDEX.md").write_text(index_content, encoding="utf-8")
    
    # Generate per-domain docs
    by_domain = defaultdict(list)
    for tag_id, tag in tags.items():
        domain = tag.get("domain", "Uncategorized")
        by_domain[domain].append((tag_id, tag))
    
    for domain, domain_tags in by_domain.items():
        domain_slug = domain.replace(" ", "_").replace(".", "").replace("/", "_").lower()
        print(f"  Generating {domain_slug}.md...")
        domain_content = generate_domain_doc(domain, sorted(domain_tags))
        (output_dir / f"{domain_slug}.md").write_text(domain_content, encoding="utf-8")
    
    # Generate stats
    print("Generating stats.json...")
    stats = generate_stats(tags, args.version)
    (output_dir / "stats.json").write_text(
        json.dumps(stats, indent=2),
        encoding="utf-8"
    )
    
    print()
    print(f"Documentation generated in {output_dir}/")
    print(f"  - INDEX.md")
    print(f"  - {len(by_domain)} domain files")
    print(f"  - stats.json")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
