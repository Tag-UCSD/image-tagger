#!/usr/bin/env python3
"""
TRS-901: Tag quality score calculator.

Calculates a quality score for each tag based on:
- Definition quality (length, clarity)
- Field completeness
- Documentation coverage
- Extractability information
- Literature references

Usage:
    python scripts/quality_score.py v0.2.8
    python scripts/quality_score.py v0.2.8 --output scores.json
    python scripts/quality_score.py v0.2.8 --threshold 0.5
"""

from __future__ import annotations
import argparse
import json
import re
import sys
from dataclasses import dataclass, field
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


@dataclass
class QualityScore:
    """Quality score for a tag."""
    tag_id: str
    total_score: float
    max_score: float
    percentage: float
    breakdown: dict[str, float] = field(default_factory=dict)
    issues: list[str] = field(default_factory=list)
    
    @classmethod
    def calculate(cls, tag_id: str, tag: dict) -> "QualityScore":
        """Calculate quality score for a tag."""
        score = 0.0
        max_score = 0.0
        breakdown = {}
        issues = []
        
        # 1. Definition quality (30 points)
        max_score += 30
        definition = tag.get("definition", "")
        
        if definition:
            def_score = 0
            
            # Length check (10 pts)
            if len(definition) >= 50:
                def_score += 10
            elif len(definition) >= 20:
                def_score += 5
            else:
                issues.append("Definition too short")
            
            # Not a placeholder (10 pts)
            if "operational tag" not in definition.lower():
                def_score += 10
            else:
                issues.append("Contains placeholder text")
            
            # Proper punctuation (5 pts)
            if definition.strip().endswith(('.', '?', '!')):
                def_score += 5
            else:
                issues.append("Definition missing punctuation")
            
            # Doesn't start with article (5 pts)
            if not re.match(r'^(The|A|An)\s', definition):
                def_score += 5
            
            score += def_score
            breakdown["definition"] = def_score
        else:
            issues.append("Missing definition")
            breakdown["definition"] = 0
        
        # 2. Required fields (20 points)
        max_score += 20
        required_fields = ["canonical_name", "value_type", "status", "category"]
        required_score = sum(5 for f in required_fields if tag.get(f))
        score += required_score
        breakdown["required_fields"] = required_score
        
        missing = [f for f in required_fields if not tag.get(f)]
        if missing:
            issues.append(f"Missing required: {', '.join(missing)}")
        
        # 3. Domain information (10 points)
        max_score += 10
        if tag.get("domain"):
            score += 10
            breakdown["domain"] = 10
        else:
            issues.append("Missing domain")
            breakdown["domain"] = 0
        
        # 4. Extractability info (15 points)
        max_score += 15
        extract = tag.get("extractability", {})
        
        if extract:
            ext_score = 0
            if extract.get("from_2d"):
                ext_score += 5
            if extract.get("from_3d_vr"):
                ext_score += 5
            if extract.get("monocular_3d_approx"):
                ext_score += 5
            
            score += ext_score
            breakdown["extractability"] = ext_score
            
            if ext_score < 15:
                issues.append("Incomplete extractability info")
        else:
            issues.append("Missing extractability")
            breakdown["extractability"] = 0
        
        # 5. Semantics / Aliases (10 points)
        max_score += 10
        semantics = tag.get("semantics", {})
        
        if semantics:
            sem_score = 0
            aliases = semantics.get("aliases", [])
            
            if aliases:
                sem_score += min(len(aliases) * 2, 10)
            
            score += sem_score
            breakdown["semantics"] = sem_score
        else:
            breakdown["semantics"] = 0
        
        # 6. Literature references (10 points)
        max_score += 10
        literature = tag.get("literature", {})
        
        if literature:
            lit_score = 0
            if literature.get("key_references"):
                lit_score += 5
            if literature.get("search_terms"):
                lit_score += 5
            
            score += lit_score
            breakdown["literature"] = lit_score
        else:
            breakdown["literature"] = 0
        
        # 7. BN information (5 points)
        max_score += 5
        bn = tag.get("bn", {})
        
        if bn and any(bn.values()):
            score += 5
            breakdown["bn"] = 5
        else:
            breakdown["bn"] = 0
        
        percentage = (score / max_score * 100) if max_score > 0 else 0
        
        return cls(
            tag_id=tag_id,
            total_score=score,
            max_score=max_score,
            percentage=round(percentage, 1),
            breakdown=breakdown,
            issues=issues,
        )


def calculate_all_scores(tags: dict) -> list[QualityScore]:
    """Calculate quality scores for all tags."""
    scores = []
    for tag_id, tag in tags.items():
        if isinstance(tag, dict):
            scores.append(QualityScore.calculate(tag_id, tag))
    return scores


def generate_report(scores: list[QualityScore]) -> dict:
    """Generate summary report."""
    if not scores:
        return {"error": "No scores"}
    
    percentages = [s.percentage for s in scores]
    
    # Grade distribution
    excellent = sum(1 for p in percentages if p >= 80)
    good = sum(1 for p in percentages if 60 <= p < 80)
    fair = sum(1 for p in percentages if 40 <= p < 60)
    poor = sum(1 for p in percentages if p < 40)
    
    # Common issues
    all_issues = []
    for s in scores:
        all_issues.extend(s.issues)
    
    issue_counts = {}
    for issue in all_issues:
        issue_counts[issue] = issue_counts.get(issue, 0) + 1
    
    top_issues = sorted(issue_counts.items(), key=lambda x: -x[1])[:10]
    
    return {
        "total_tags": len(scores),
        "average_score": round(sum(percentages) / len(percentages), 1),
        "distribution": {
            "excellent_80+": excellent,
            "good_60-79": good,
            "fair_40-59": fair,
            "poor_below_40": poor,
        },
        "top_issues": [{"issue": i, "count": c} for i, c in top_issues],
        "lowest_scores": [
            {"tag_id": s.tag_id, "score": s.percentage}
            for s in sorted(scores, key=lambda x: x.percentage)[:20]
        ],
    }


def main():
    parser = argparse.ArgumentParser(description="Calculate tag quality scores")
    parser.add_argument("version", help="Registry version (e.g., v0.2.8)")
    parser.add_argument("--output", "-o", help="Output JSON file")
    parser.add_argument("--threshold", type=float, default=0, help="Only show below threshold")
    parser.add_argument("--details", action="store_true", help="Show detailed breakdown")
    args = parser.parse_args()

    print(f"Calculating quality scores for {args.version}...")
    
    registry = load_registry(args.version)
    tags = registry.get("tags", {})
    print(f"  Found {len(tags)} tags")
    
    scores = calculate_all_scores(tags)
    report = generate_report(scores)
    
    print()
    print("=" * 60)
    print("QUALITY REPORT")
    print("=" * 60)
    print()
    print(f"Average Score: {report['average_score']}%")
    print()
    print("Distribution:")
    for grade, count in report["distribution"].items():
        pct = count / len(scores) * 100
        print(f"  {grade}: {count} ({pct:.1f}%)")
    
    print()
    print("Top Issues:")
    for item in report["top_issues"][:5]:
        print(f"  {item['count']:3} tags: {item['issue']}")
    
    # Filter by threshold
    if args.threshold > 0:
        below = [s for s in scores if s.percentage < args.threshold]
        print()
        print(f"Tags below {args.threshold}% ({len(below)}):")
        for s in sorted(below, key=lambda x: x.percentage)[:20]:
            print(f"  {s.percentage:5.1f}% | {s.tag_id}")
            if args.details:
                for issue in s.issues:
                    print(f"         - {issue}")
    
    # Output to file
    if args.output:
        output = {
            "version": args.version,
            "report": report,
            "scores": [
                {
                    "tag_id": s.tag_id,
                    "percentage": s.percentage,
                    "breakdown": s.breakdown,
                    "issues": s.issues,
                }
                for s in scores
            ],
        }
        Path(args.output).write_text(json.dumps(output, indent=2), encoding="utf-8")
        print(f"\nDetailed results written to {args.output}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
