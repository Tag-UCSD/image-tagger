#!/usr/bin/env python3
"""
TRS-504: Registry linting - style and quality checks.

Usage:
    python scripts/lint_registry.py v0.2.8
    python scripts/lint_registry.py v0.2.8 --fix
    python scripts/lint_registry.py v0.2.8 --strict

Checks:
- Naming conventions (canonical_name capitalization)
- Definition quality (length, punctuation)
- Missing recommended fields
- Alias consistency
- Domain naming consistency
- Tag ID format
"""

from __future__ import annotations
import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent


@dataclass
class LintIssue:
    tag_id: str
    level: str  # error, warning, info
    code: str
    message: str
    fix: str = ""


def load_registry(version: str) -> tuple[dict, Path]:
    """Load registry for a version."""
    registry_dir = REPO_ROOT / "core" / "trs-core" / version / "registry"
    yamls = sorted(list(registry_dir.glob("*.yml")) + list(registry_dir.glob("*.yaml")))
    if not yamls:
        raise FileNotFoundError(f"No registry YAML in {registry_dir}")
    return yaml.safe_load(yamls[0].read_text(encoding="utf-8")), yamls[0]


class RegistryLinter:
    """Lint registry for style and quality issues."""
    
    def __init__(self, strict: bool = False):
        self.strict = strict
        self.issues: list[LintIssue] = []
    
    def lint(self, tags: dict) -> list[LintIssue]:
        """Run all lint checks."""
        self.issues = []
        
        for tag_id, tag in tags.items():
            if not isinstance(tag, dict):
                continue
            
            self._check_tag_id(tag_id)
            self._check_canonical_name(tag_id, tag)
            self._check_definition(tag_id, tag)
            self._check_domain(tag_id, tag)
            self._check_aliases(tag_id, tag)
            self._check_extractability(tag_id, tag)
            self._check_required_fields(tag_id, tag)
        
        return self.issues
    
    def _add(self, tag_id: str, level: str, code: str, message: str, fix: str = ""):
        self.issues.append(LintIssue(tag_id, level, code, message, fix))
    
    def _check_tag_id(self, tag_id: str):
        """Check tag ID format."""
        # Should be lowercase with dots and underscores
        if not re.match(r'^[a-z][a-z0-9_]*(\.[a-z0-9_/()+-]+){1,5}$', tag_id, re.IGNORECASE):
            self._add(tag_id, "warning", "TID001", 
                     f"Non-standard tag ID format: {tag_id}")
        
        # Check for uppercase
        if tag_id != tag_id.lower():
            self._add(tag_id, "info", "TID002",
                     f"Tag ID contains uppercase: {tag_id}",
                     fix=tag_id.lower())
    
    def _check_canonical_name(self, tag_id: str, tag: dict):
        """Check canonical name style."""
        name = tag.get("canonical_name", "")
        
        if not name:
            self._add(tag_id, "error", "NAM001", "Missing canonical_name")
            return
        
        # Should be Title Case or have at least first letter capitalized
        if name[0].islower():
            self._add(tag_id, "warning", "NAM002",
                     f"Canonical name should start with capital: '{name}'",
                     fix=name.capitalize())
        
        # Check for excessive abbreviations
        if len(name) < 3:
            self._add(tag_id, "info", "NAM003",
                     f"Very short canonical name: '{name}'")
    
    def _check_definition(self, tag_id: str, tag: dict):
        """Check definition quality."""
        definition = tag.get("definition", "")
        
        if not definition:
            self._add(tag_id, "warning", "DEF001", "Missing definition")
            return
        
        # Too short
        if len(definition) < 20:
            self._add(tag_id, "warning", "DEF002",
                     f"Definition too short ({len(definition)} chars)")
        
        # Doesn't end with period
        if definition and not definition.rstrip().endswith(('.', '?', '!')):
            self._add(tag_id, "info", "DEF003",
                     "Definition should end with punctuation",
                     fix=definition.rstrip() + ".")
        
        # Starts with "The" or "A" (weak opening)
        if re.match(r'^(The|A|An)\s', definition):
            self._add(tag_id, "info", "DEF004",
                     "Definition starts with article (consider stronger opening)")
        
        # Contains "operational tag" (placeholder)
        if "operational tag" in definition.lower():
            self._add(tag_id, "warning", "DEF005",
                     "Definition contains placeholder text 'operational tag'")
    
    def _check_domain(self, tag_id: str, tag: dict):
        """Check domain field."""
        domain = tag.get("domain", "")
        
        if not domain:
            self._add(tag_id, "warning", "DOM001", "Missing domain")
            return
        
        # Check for consistency (should have letter prefix like "A. ")
        if self.strict and not re.match(r'^[A-Z]\.\s', domain):
            self._add(tag_id, "info", "DOM002",
                     f"Domain doesn't follow 'X. Name' format: '{domain}'")
    
    def _check_aliases(self, tag_id: str, tag: dict):
        """Check aliases quality."""
        semantics = tag.get("semantics", {})
        if not isinstance(semantics, dict):
            return
        
        aliases = semantics.get("aliases", [])
        
        # Check for duplicate aliases within same tag
        seen = set()
        for alias in aliases:
            alias_lower = str(alias).lower()
            if alias_lower in seen:
                self._add(tag_id, "warning", "ALI001",
                         f"Duplicate alias (case-insensitive): '{alias}'")
            seen.add(alias_lower)
        
        # Check alias matches canonical name
        canonical = tag.get("canonical_name", "").lower()
        if canonical in seen:
            self._add(tag_id, "info", "ALI002",
                     "Canonical name duplicated in aliases (redundant)")
    
    def _check_extractability(self, tag_id: str, tag: dict):
        """Check extractability field."""
        extract = tag.get("extractability", {})
        
        if not extract:
            if self.strict:
                self._add(tag_id, "info", "EXT001", "Missing extractability")
            return
        
        valid_values = {"yes", "no", "partial", "n/a", "na", ""}
        
        for key in ["from_2d", "from_3d_vr", "monocular_3d_approx"]:
            value = str(extract.get(key, "")).lower()
            if value and value not in valid_values:
                self._add(tag_id, "warning", "EXT002",
                         f"Invalid extractability value for {key}: '{value}'")
    
    def _check_required_fields(self, tag_id: str, tag: dict):
        """Check for recommended fields."""
        required = ["canonical_name", "value_type", "status"]
        recommended = ["definition", "domain", "category"]
        
        for field in required:
            if not tag.get(field):
                self._add(tag_id, "error", "REQ001",
                         f"Missing required field: {field}")
        
        if self.strict:
            for field in recommended:
                if not tag.get(field):
                    self._add(tag_id, "info", "REQ002",
                             f"Missing recommended field: {field}")


def main():
    parser = argparse.ArgumentParser(description="Lint registry for style issues")
    parser.add_argument("version", help="Registry version (e.g., v0.2.8)")
    parser.add_argument("--strict", action="store_true", help="Enable strict mode")
    parser.add_argument("--fix", action="store_true", help="Show suggested fixes")
    parser.add_argument("--level", choices=["error", "warning", "info"], 
                       default="warning", help="Minimum level to show")
    args = parser.parse_args()

    print(f"Linting {args.version}...")
    
    registry, path = load_registry(args.version)
    tags = registry.get("tags", {})
    print(f"  Found {len(tags)} tags")
    print()
    
    linter = RegistryLinter(strict=args.strict)
    issues = linter.lint(tags)
    
    # Filter by level
    level_order = {"error": 0, "warning": 1, "info": 2}
    min_level = level_order[args.level]
    issues = [i for i in issues if level_order[i.level] <= min_level]
    
    # Sort by level, then tag_id
    issues.sort(key=lambda x: (level_order[x.level], x.tag_id))
    
    # Display
    if not issues:
        print("✅ No issues found!")
        return 0
    
    # Group by level
    errors = [i for i in issues if i.level == "error"]
    warnings = [i for i in issues if i.level == "warning"]
    infos = [i for i in issues if i.level == "info"]
    
    if errors:
        print(f"❌ Errors ({len(errors)}):")
        for i in errors[:20]:
            print(f"  [{i.code}] {i.tag_id}: {i.message}")
            if args.fix and i.fix:
                print(f"         Fix: {i.fix}")
        if len(errors) > 20:
            print(f"  ... and {len(errors) - 20} more")
        print()
    
    if warnings:
        print(f"⚠️  Warnings ({len(warnings)}):")
        for i in warnings[:30]:
            print(f"  [{i.code}] {i.tag_id}: {i.message}")
            if args.fix and i.fix:
                print(f"         Fix: {i.fix}")
        if len(warnings) > 30:
            print(f"  ... and {len(warnings) - 30} more")
        print()
    
    if infos and args.level == "info":
        print(f"ℹ️  Info ({len(infos)}):")
        for i in infos[:20]:
            print(f"  [{i.code}] {i.tag_id}: {i.message}")
        if len(infos) > 20:
            print(f"  ... and {len(infos) - 20} more")
        print()
    
    print("=" * 50)
    print(f"Summary: {len(errors)} errors, {len(warnings)} warnings, {len(infos)} info")
    
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
