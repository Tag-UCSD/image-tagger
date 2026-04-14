#!/usr/bin/env python3
"""
TRS-503: Detect duplicate and similar tags in the registry.

Usage:
    python scripts/find_duplicates.py v0.2.8
    python scripts/find_duplicates.py v0.2.8 --threshold 0.8
    python scripts/find_duplicates.py v0.2.8 --output duplicates.json

Detects:
- Exact duplicate aliases
- Similar tag names (fuzzy matching)
- Similar definitions
- Potential tag consolidation opportunities
"""

from __future__ import annotations
import argparse
import json
import sys
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent


def load_registry(version: str) -> dict:
    """Load registry for a version."""
    registry_dir = REPO_ROOT / "core" / "trs-core" / version / "registry"
    yamls = sorted(list(registry_dir.glob("*.yml")) + list(registry_dir.glob("*.yaml")))
    if not yamls:
        raise FileNotFoundError(f"No registry YAML in {registry_dir}")
    return yaml.safe_load(yamls[0].read_text(encoding="utf-8"))


def similarity(a: str, b: str) -> float:
    """Calculate string similarity (0.0 to 1.0)."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def find_duplicate_aliases(tags: dict) -> list[dict]:
    """Find tags that share the same alias."""
    alias_to_tags = defaultdict(list)
    
    for tag_id, tag in tags.items():
        if not isinstance(tag, dict):
            continue
        
        # Collect all searchable names
        names = [tag_id.lower()]
        
        canonical = tag.get("canonical_name", "")
        if canonical:
            names.append(canonical.lower())
        
        semantics = tag.get("semantics", {})
        if isinstance(semantics, dict):
            for alias in semantics.get("aliases", []):
                if alias:
                    names.append(str(alias).lower())
        
        for name in names:
            alias_to_tags[name].append(tag_id)
    
    # Find duplicates
    duplicates = []
    for alias, tag_ids in alias_to_tags.items():
        if len(tag_ids) > 1:
            duplicates.append({
                "alias": alias,
                "tag_ids": sorted(tag_ids),
                "count": len(tag_ids),
            })
    
    return sorted(duplicates, key=lambda x: -x["count"])


def find_similar_names(tags: dict, threshold: float = 0.85) -> list[dict]:
    """Find tags with similar canonical names."""
    tag_names = []
    for tag_id, tag in tags.items():
        if isinstance(tag, dict):
            name = tag.get("canonical_name", tag_id)
            tag_names.append((tag_id, name))
    
    similar = []
    seen = set()
    
    for i, (id1, name1) in enumerate(tag_names):
        for id2, name2 in tag_names[i+1:]:
            if (id1, id2) in seen or (id2, id1) in seen:
                continue
            
            score = similarity(name1, name2)
            if score >= threshold:
                similar.append({
                    "tag1": {"id": id1, "name": name1},
                    "tag2": {"id": id2, "name": name2},
                    "similarity": round(score, 3),
                })
                seen.add((id1, id2))
    
    return sorted(similar, key=lambda x: -x["similarity"])


def find_similar_definitions(tags: dict, threshold: float = 0.7) -> list[dict]:
    """Find tags with similar definitions."""
    tag_defs = []
    for tag_id, tag in tags.items():
        if isinstance(tag, dict):
            definition = tag.get("definition", "")
            if definition and len(definition) > 20:  # Skip short/empty
                tag_defs.append((tag_id, definition))
    
    similar = []
    seen = set()
    
    for i, (id1, def1) in enumerate(tag_defs):
        for id2, def2 in tag_defs[i+1:]:
            if (id1, id2) in seen or (id2, id1) in seen:
                continue
            
            # Skip if definitions are very different lengths
            if abs(len(def1) - len(def2)) > max(len(def1), len(def2)) * 0.5:
                continue
            
            score = similarity(def1, def2)
            if score >= threshold:
                similar.append({
                    "tag1": {"id": id1, "definition": def1[:100]},
                    "tag2": {"id": id2, "definition": def2[:100]},
                    "similarity": round(score, 3),
                })
                seen.add((id1, id2))
    
    return sorted(similar, key=lambda x: -x["similarity"])


def find_consolidation_candidates(tags: dict) -> list[dict]:
    """Find tags that might be candidates for consolidation."""
    candidates = []
    
    # Group by domain and value_type
    groups = defaultdict(list)
    for tag_id, tag in tags.items():
        if not isinstance(tag, dict):
            continue
        key = (tag.get("domain", ""), tag.get("value_type", ""))
        groups[key].append((tag_id, tag))
    
    # Look for similar tags within same domain/type
    for (domain, vtype), group_tags in groups.items():
        if len(group_tags) < 2:
            continue
        
        for i, (id1, tag1) in enumerate(group_tags):
            name1 = tag1.get("canonical_name", "")
            for id2, tag2 in group_tags[i+1:]:
                name2 = tag2.get("canonical_name", "")
                
                # Check name similarity
                name_sim = similarity(name1, name2)
                
                # Check definition similarity
                def1 = tag1.get("definition", "")
                def2 = tag2.get("definition", "")
                def_sim = similarity(def1, def2) if def1 and def2 else 0
                
                # Combined score
                combined = (name_sim * 0.4 + def_sim * 0.6)
                
                if combined >= 0.6:
                    candidates.append({
                        "tag1": id1,
                        "tag2": id2,
                        "domain": domain,
                        "name_similarity": round(name_sim, 3),
                        "definition_similarity": round(def_sim, 3),
                        "combined_score": round(combined, 3),
                    })
    
    return sorted(candidates, key=lambda x: -x["combined_score"])


def main():
    parser = argparse.ArgumentParser(description="Find duplicate and similar tags")
    parser.add_argument("version", help="Registry version (e.g., v0.2.8)")
    parser.add_argument("--threshold", type=float, default=0.85, help="Similarity threshold")
    parser.add_argument("--output", "-o", help="Output JSON file")
    args = parser.parse_args()

    print(f"Analyzing {args.version}...")
    
    registry = load_registry(args.version)
    tags = registry.get("tags", {})
    print(f"  Found {len(tags)} tags")
    print()
    
    results = {
        "version": args.version,
        "total_tags": len(tags),
        "threshold": args.threshold,
    }
    
    # Find duplicate aliases
    print("Finding duplicate aliases...")
    dup_aliases = find_duplicate_aliases(tags)
    results["duplicate_aliases"] = dup_aliases
    print(f"  Found {len(dup_aliases)} duplicate aliases")
    
    # Find similar names
    print("Finding similar names...")
    similar_names = find_similar_names(tags, args.threshold)
    results["similar_names"] = similar_names[:50]  # Top 50
    print(f"  Found {len(similar_names)} similar name pairs")
    
    # Find similar definitions
    print("Finding similar definitions...")
    similar_defs = find_similar_definitions(tags, args.threshold - 0.15)
    results["similar_definitions"] = similar_defs[:50]  # Top 50
    print(f"  Found {len(similar_defs)} similar definition pairs")
    
    # Find consolidation candidates
    print("Finding consolidation candidates...")
    candidates = find_consolidation_candidates(tags)
    results["consolidation_candidates"] = candidates[:30]  # Top 30
    print(f"  Found {len(candidates)} consolidation candidates")
    
    # Output
    if args.output:
        Path(args.output).write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"\nResults written to {args.output}")
    else:
        print()
        print("=" * 60)
        print("SUMMARY")
        print("=" * 60)
        
        if dup_aliases:
            print(f"\n⚠️  Duplicate Aliases ({len(dup_aliases)}):")
            for dup in dup_aliases[:10]:
                print(f"  '{dup['alias']}' used by: {', '.join(dup['tag_ids'][:3])}")
        
        if similar_names:
            print(f"\n🔍 Similar Names ({len(similar_names)}):")
            for sim in similar_names[:5]:
                print(f"  {sim['tag1']['name']} ↔ {sim['tag2']['name']} ({sim['similarity']:.0%})")
        
        if candidates:
            print(f"\n🔄 Consolidation Candidates ({len(candidates)}):")
            for c in candidates[:5]:
                print(f"  {c['tag1']} ↔ {c['tag2']} (score: {c['combined_score']:.0%})")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
