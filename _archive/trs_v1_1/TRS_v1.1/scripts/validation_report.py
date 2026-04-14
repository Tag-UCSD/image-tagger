#!/usr/bin/env python3
"""
TRS-904: Comprehensive data validation report.

Generates a detailed report on registry data quality.

Usage:
    python scripts/validation_report.py v0.2.8
    python scripts/validation_report.py v0.2.8 --output report.md
    python scripts/validation_report.py v0.2.8 --format json
"""

from __future__ import annotations
import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime
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


def analyze_registry(registry: dict) -> dict:
    """Perform comprehensive analysis of registry."""
    tags = registry.get("tags", {})
    
    results = {
        "metadata": {
            "total_tags": len(tags),
            "content_version": registry.get("content_version"),
            "generated_at": registry.get("generated_at_utc"),
        },
        "completeness": {},
        "quality": {},
        "consistency": {},
        "distribution": {},
        "issues": [],
    }
    
    # ========================================================================
    # Completeness Analysis
    # ========================================================================
    
    field_presence = defaultdict(int)
    required_fields = ["canonical_name", "value_type", "status", "definition"]
    recommended_fields = ["domain", "category", "extractability"]
    
    for tag_id, tag in tags.items():
        if not isinstance(tag, dict):
            continue
        
        for field in required_fields + recommended_fields + ["semantics", "literature", "bn"]:
            if tag.get(field):
                field_presence[field] += 1
    
    results["completeness"]["field_coverage"] = {
        field: {
            "count": field_presence[field],
            "percentage": round(field_presence[field] / len(tags) * 100, 1),
        }
        for field in required_fields + recommended_fields
    }
    
    # Missing required fields
    missing_required = []
    for tag_id, tag in tags.items():
        if not isinstance(tag, dict):
            continue
        missing = [f for f in required_fields if not tag.get(f)]
        if missing:
            missing_required.append({"tag_id": tag_id, "missing": missing})
    
    results["completeness"]["missing_required"] = missing_required[:50]
    results["completeness"]["tags_missing_required"] = len(missing_required)
    
    # ========================================================================
    # Quality Analysis
    # ========================================================================
    
    # Definition quality
    definition_issues = {
        "too_short": [],
        "placeholder": [],
        "no_punctuation": [],
    }
    
    for tag_id, tag in tags.items():
        if not isinstance(tag, dict):
            continue
        
        definition = tag.get("definition", "")
        
        if not definition:
            continue
        
        if len(definition) < 20:
            definition_issues["too_short"].append(tag_id)
        
        if "operational tag" in definition.lower():
            definition_issues["placeholder"].append(tag_id)
        
        if not definition.strip().endswith(('.', '?', '!')):
            definition_issues["no_punctuation"].append(tag_id)
    
    results["quality"]["definitions"] = {
        k: {"count": len(v), "examples": v[:5]}
        for k, v in definition_issues.items()
    }
    
    # ========================================================================
    # Consistency Analysis
    # ========================================================================
    
    # Domain consistency
    domains = defaultdict(list)
    for tag_id, tag in tags.items():
        if isinstance(tag, dict):
            domain = tag.get("domain", "NONE")
            domains[domain].append(tag_id)
    
    results["consistency"]["domains"] = {
        domain: {"count": len(tag_ids), "sample": tag_ids[:3]}
        for domain, tag_ids in sorted(domains.items(), key=lambda x: -len(x[1]))
    }
    
    # Value type distribution
    value_types = defaultdict(int)
    for tag in tags.values():
        if isinstance(tag, dict):
            value_types[tag.get("value_type", "NONE")] += 1
    
    results["consistency"]["value_types"] = dict(value_types)
    
    # Status distribution
    statuses = defaultdict(int)
    for tag in tags.values():
        if isinstance(tag, dict):
            statuses[tag.get("status", "NONE")] += 1
    
    results["consistency"]["statuses"] = dict(statuses)
    
    # Duplicate aliases
    alias_map = defaultdict(list)
    for tag_id, tag in tags.items():
        if not isinstance(tag, dict):
            continue
        
        semantics = tag.get("semantics", {})
        if not isinstance(semantics, dict):
            continue
        
        for alias in semantics.get("aliases", []):
            alias_map[str(alias).lower()].append(tag_id)
    
    duplicate_aliases = {
        alias: tag_ids
        for alias, tag_ids in alias_map.items()
        if len(tag_ids) > 1
    }
    
    results["consistency"]["duplicate_aliases"] = {
        "count": len(duplicate_aliases),
        "examples": dict(list(duplicate_aliases.items())[:10]),
    }
    
    # ========================================================================
    # Distribution Analysis
    # ========================================================================
    
    # Tags per domain
    results["distribution"]["by_domain"] = {
        domain: len(tag_ids)
        for domain, tag_ids in sorted(domains.items(), key=lambda x: -len(x[1]))
    }
    
    # Extractability coverage
    extractable_2d = 0
    extractable_3d = 0
    
    for tag in tags.values():
        if not isinstance(tag, dict):
            continue
        
        extract = tag.get("extractability", {})
        if extract.get("from_2d") == "yes":
            extractable_2d += 1
        if extract.get("from_3d_vr") == "yes":
            extractable_3d += 1
    
    results["distribution"]["extractability"] = {
        "from_2d_yes": extractable_2d,
        "from_3d_vr_yes": extractable_3d,
    }
    
    # ========================================================================
    # Issues Summary
    # ========================================================================
    
    issues = []
    
    if results["completeness"]["tags_missing_required"] > 0:
        issues.append({
            "severity": "error",
            "category": "completeness",
            "message": f"{results['completeness']['tags_missing_required']} tags missing required fields",
        })
    
    if definition_issues["placeholder"]:
        issues.append({
            "severity": "warning",
            "category": "quality",
            "message": f"{len(definition_issues['placeholder'])} tags have placeholder definitions",
        })
    
    if duplicate_aliases:
        issues.append({
            "severity": "warning",
            "category": "consistency",
            "message": f"{len(duplicate_aliases)} duplicate aliases found",
        })
    
    results["issues"] = issues
    
    return results


def format_markdown(results: dict, version: str) -> str:
    """Format results as Markdown report."""
    lines = [
        f"# Registry Validation Report: {version}",
        f"",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"",
        f"## Summary",
        f"",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total Tags | {results['metadata']['total_tags']} |",
        f"| Content Version | {results['metadata']['content_version']} |",
        f"| Issues Found | {len(results['issues'])} |",
        f"",
    ]
    
    # Issues
    if results["issues"]:
        lines.extend([
            f"## Issues",
            f"",
        ])
        for issue in results["issues"]:
            icon = "❌" if issue["severity"] == "error" else "⚠️"
            lines.append(f"- {icon} **{issue['category']}**: {issue['message']}")
        lines.append("")
    
    # Completeness
    lines.extend([
        f"## Field Completeness",
        f"",
        f"| Field | Coverage |",
        f"|-------|----------|",
    ])
    
    for field, data in results["completeness"]["field_coverage"].items():
        lines.append(f"| {field} | {data['percentage']}% ({data['count']}) |")
    
    lines.append("")
    
    # Distribution
    lines.extend([
        f"## Distribution",
        f"",
        f"### By Domain",
        f"",
    ])
    
    for domain, count in list(results["distribution"]["by_domain"].items())[:15]:
        domain_short = domain[:40] + "..." if len(domain) > 40 else domain
        lines.append(f"- {domain_short}: {count}")
    
    lines.extend([
        f"",
        f"### By Value Type",
        f"",
    ])
    
    for vtype, count in results["consistency"]["value_types"].items():
        lines.append(f"- {vtype}: {count}")
    
    lines.extend([
        f"",
        f"### By Status",
        f"",
    ])
    
    for status, count in results["consistency"]["statuses"].items():
        lines.append(f"- {status}: {count}")
    
    # Quality
    lines.extend([
        f"",
        f"## Definition Quality",
        f"",
    ])
    
    for issue_type, data in results["quality"]["definitions"].items():
        lines.append(f"- **{issue_type}**: {data['count']} tags")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate validation report")
    parser.add_argument("version", help="Registry version (e.g., v0.2.8)")
    parser.add_argument("--output", "-o", help="Output file")
    parser.add_argument("--format", "-f", default="markdown", choices=["markdown", "json"])
    args = parser.parse_args()

    print(f"Analyzing {args.version}...")
    
    registry = load_registry(args.version)
    results = analyze_registry(registry)
    
    print(f"  Total tags: {results['metadata']['total_tags']}")
    print(f"  Issues found: {len(results['issues'])}")
    
    # Format output
    if args.format == "json":
        output = json.dumps(results, indent=2)
    else:
        output = format_markdown(results, args.version)
    
    # Write or print
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"\nReport written to {args.output}")
    else:
        print()
        print(output)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
