#!/usr/bin/env python3
"""
TRS-102 + TRS-103: Validate registry schema and semantic invariants.

Usage:
    python scripts/validate_registry.py core/trs-core/v0.2.8/registry/
    python scripts/validate_registry.py core/trs-core/v0.2.8/registry/ --verbose
    python scripts/validate_registry.py core/trs-core/v0.2.8/registry/ --json

Validation includes:
1. Schema validation (structure, required fields, enum values)
2. Invariant validation (semantic constraints JSON Schema can't express)

Exit codes:
    0 = All validations passed
    1 = Validation errors found
    2 = Failed to load registry
"""

from __future__ import annotations
import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


# ============================================================================
# Schema Definitions
# ============================================================================

VALID_VALUE_TYPES = {"binary", "ordinal", "continuous", "categorical", "multilabel", "region_map", "latent_score"}
VALID_EXTRACTABILITY = {"yes", "partial", "no"}
VALID_STATUSES = {"active", "deprecated", "experimental", "proposed", "existing", "proposed_delta"}
VALID_CATEGORIES = {"environmental", "cognitive", "physiological", "preference", "derived"}
VALID_EVIDENCE_ROLES = {"stimulus_antecedent", "latent", "outcome", "moderator", "derived_metric", "marker"}
VALID_DEMAND_STATES = {"required", "optional", "exploratory", "not_applicable"}

# Allow 2-6 part tag IDs with common special chars found in registry
# Examples: env.ae.cool_lighting_(high_cct), env.ae.stone/marble_prominent
TAG_ID_PATTERN = re.compile(r'^[a-z][a-z0-9_]*(\.[a-z0-9_/()+-]+){1,5}$', re.IGNORECASE)


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class ValidationError:
    """A single validation error."""
    tag_id: str
    field: str
    message: str
    severity: str = "error"  # error, warning

    def __str__(self):
        return f"[{self.severity.upper()}] {self.tag_id}: {self.field} - {self.message}"


@dataclass
class ValidationResult:
    """Collection of validation results."""
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[ValidationError] = field(default_factory=list)
    tag_count: int = 0
    
    def add_error(self, tag_id: str, field_name: str, message: str):
        self.errors.append(ValidationError(tag_id, field_name, message, "error"))
    
    def add_warning(self, tag_id: str, field_name: str, message: str):
        self.warnings.append(ValidationError(tag_id, field_name, message, "warning"))
    
    @property
    def passed(self) -> bool:
        return len(self.errors) == 0
    
    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "tag_count": self.tag_count,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "errors": [{"tag_id": e.tag_id, "field": e.field, "message": e.message} for e in self.errors],
            "warnings": [{"tag_id": w.tag_id, "field": w.field, "message": w.message} for w in self.warnings],
        }


# ============================================================================
# Schema Validation
# ============================================================================

def validate_tag_schema(tag_id: str, tag: dict, result: ValidationResult) -> None:
    """Validate a single tag against the schema."""
    
    # Required fields
    required_fields = ["canonical_name", "category", "value_type", "status"]
    for field_name in required_fields:
        if field_name not in tag or tag[field_name] is None:
            result.add_error(tag_id, field_name, f"Required field missing")
    
    # Tag ID format
    if not TAG_ID_PATTERN.match(tag_id):
        result.add_error(tag_id, "tag_id", f"Invalid format. Expected: category.domain.attribute")
    
    # Enum validations
    if tag.get("value_type") and tag["value_type"] not in VALID_VALUE_TYPES:
        result.add_error(tag_id, "value_type", f"Invalid value '{tag['value_type']}'. Must be one of: {VALID_VALUE_TYPES}")
    
    if tag.get("status") and tag["status"] not in VALID_STATUSES:
        result.add_error(tag_id, "status", f"Invalid value '{tag['status']}'. Must be one of: {VALID_STATUSES}")
    
    if tag.get("category") and tag["category"] not in VALID_CATEGORIES:
        result.add_error(tag_id, "category", f"Invalid value '{tag['category']}'. Must be one of: {VALID_CATEGORIES}")
    
    # Extractability validation
    extractability = tag.get("extractability", {})
    for key in ["from_2d", "from_3d_vr", "monocular_3d_approx"]:
        val = extractability.get(key)
        if val is not None and val not in VALID_EXTRACTABILITY:
            result.add_error(tag_id, f"extractability.{key}", f"Invalid value '{val}'. Must be one of: {VALID_EXTRACTABILITY}")
    
    # BN field validation
    bn = tag.get("bn", {})
    if bn.get("evidence_role") and bn["evidence_role"] not in VALID_EVIDENCE_ROLES:
        result.add_error(tag_id, "bn.evidence_role", f"Invalid value '{bn['evidence_role']}'. Must be one of: {VALID_EVIDENCE_ROLES}")
    
    if bn.get("demand_state") and bn["demand_state"] not in VALID_DEMAND_STATES:
        result.add_error(tag_id, "bn.demand_state", f"Invalid value '{bn['demand_state']}'. Must be one of: {VALID_DEMAND_STATES}")
    
    # Warnings for recommended fields
    if tag.get("status") == "active":
        if not tag.get("definition"):
            result.add_warning(tag_id, "definition", "Active tag should have a definition")
        if not tag.get("domain"):
            result.add_warning(tag_id, "domain", "Active tag should have a domain")


# ============================================================================
# Invariant Validation
# ============================================================================

def validate_invariants(tags: dict[str, dict], result: ValidationResult) -> None:
    """Validate semantic invariants across all tags."""
    
    all_tag_ids = set(tags.keys())
    alias_registry: dict[str, str] = {}  # alias -> tag_id
    
    for tag_id, tag in tags.items():
        semantics = tag.get("semantics", {})
        
        # Invariant 1: Alias uniqueness
        for alias in semantics.get("aliases", []):
            alias_lower = alias.lower().strip()
            if alias_lower in alias_registry:
                result.add_error(
                    tag_id, "semantics.aliases",
                    f"Duplicate alias '{alias}' also in {alias_registry[alias_lower]}"
                )
            else:
                alias_registry[alias_lower] = tag_id
        
        # Invariant 2: Parent reference exists
        hierarchy = semantics.get("hierarchy", {})
        parent = hierarchy.get("parent")
        if parent and parent not in all_tag_ids:
            result.add_error(tag_id, "semantics.hierarchy.parent", f"Parent tag '{parent}' does not exist")
        
        # Invariant 3: Children references exist
        for child in hierarchy.get("children", []) or []:
            if child not in all_tag_ids:
                result.add_error(tag_id, "semantics.hierarchy.children", f"Child tag '{child}' does not exist")
        
        # Invariant 4: Related tags exist
        relations = semantics.get("relations", {})
        for related in relations.get("related_tags", []) or []:
            if related not in all_tag_ids:
                result.add_warning(tag_id, "semantics.relations.related_tags", f"Related tag '{related}' does not exist")
        
        # Invariant 5: Inverse tag exists
        inverse = relations.get("inverse_of")
        if inverse and inverse not in all_tag_ids:
            result.add_error(tag_id, "semantics.relations.inverse_of", f"Inverse tag '{inverse}' does not exist")
        
        # Invariant 6: Mutual exclusivity references exist
        for excl in relations.get("mutually_exclusive_with", []) or []:
            if excl not in all_tag_ids:
                result.add_warning(tag_id, "semantics.relations.mutually_exclusive_with", f"Exclusive tag '{excl}' does not exist")
        
        # Invariant 7: Version monotonicity
        version_added = tag.get("version_added", "0.0.0")
        version_modified = tag.get("version_modified", "0.0.0")
        if version_modified and version_added:
            if version_modified < version_added:
                result.add_error(tag_id, "version_modified", f"Version modified ({version_modified}) < version added ({version_added})")
        
        # Invariant 8: BN parent/child references exist
        bn = tag.get("bn", {})
        for parent_tag in bn.get("parent_tags", []) or []:
            if parent_tag not in all_tag_ids:
                result.add_error(tag_id, "bn.parent_tags", f"BN parent tag '{parent_tag}' does not exist")
        
        for child_tag in bn.get("child_tags", []) or []:
            if child_tag not in all_tag_ids:
                result.add_error(tag_id, "bn.child_tags", f"BN child tag '{child_tag}' does not exist")
    
    # Invariant 9: Check for circular deprecation
    deprecated_tags = {tid: t.get("replaced_by") for tid, t in tags.items() 
                       if t.get("status") == "deprecated" and t.get("replaced_by")}
    
    for start_tag, replacement in deprecated_tags.items():
        visited = {start_tag}
        current = replacement
        while current and current in deprecated_tags:
            if current in visited:
                result.add_error(start_tag, "replaced_by", f"Circular deprecation chain detected involving {current}")
                break
            visited.add(current)
            current = deprecated_tags.get(current)
    
    # Invariant 10: Deprecated tags should have replacement
    for tag_id, tag in tags.items():
        if tag.get("status") == "deprecated" and not tag.get("replaced_by"):
            result.add_warning(tag_id, "replaced_by", "Deprecated tag should specify replacement")


# ============================================================================
# Main Validation
# ============================================================================

def load_registry(registry_dir: Path) -> tuple[dict, Path]:
    """Load registry YAML."""
    yamls = sorted(list(registry_dir.glob("*.yml")) + list(registry_dir.glob("*.yaml")))
    if not yamls:
        raise FileNotFoundError(f"No registry YAML found in {registry_dir}")
    reg_path = yamls[0]
    return yaml.safe_load(reg_path.read_text(encoding="utf-8")), reg_path


def validate_registry(registry_dir: Path, verbose: bool = False) -> ValidationResult:
    """Run all validations on a registry."""
    result = ValidationResult()
    
    # Load registry
    try:
        registry, reg_path = load_registry(registry_dir)
    except Exception as e:
        result.add_error("_registry", "load", str(e))
        return result
    
    tags = registry.get("tags", {})
    if not isinstance(tags, dict):
        result.add_error("_registry", "tags", "Tags must be a dictionary")
        return result
    
    result.tag_count = len(tags)
    
    if verbose:
        print(f"Validating {len(tags)} tags from {reg_path.name}")
    
    # Schema validation
    for tag_id, tag in tags.items():
        if not isinstance(tag, dict):
            result.add_error(tag_id, "_structure", "Tag must be a dictionary")
            continue
        validate_tag_schema(tag_id, tag, result)
    
    # Invariant validation
    validate_invariants(tags, result)
    
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate registry schema and invariants")
    parser.add_argument("registry_dir", type=Path, help="Registry directory")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--warnings-as-errors", action="store_true", help="Treat warnings as errors")
    args = parser.parse_args()

    if not args.registry_dir.exists():
        print(f"ERROR: Registry directory not found: {args.registry_dir}")
        return 2

    result = validate_registry(args.registry_dir, verbose=args.verbose)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        if result.errors:
            print(f"\n=== ERRORS ({len(result.errors)}) ===")
            for err in result.errors:
                print(f"  {err}")
        
        if result.warnings:
            print(f"\n=== WARNINGS ({len(result.warnings)}) ===")
            for warn in result.warnings:
                print(f"  {warn}")
        
        print()
        if result.passed:
            print(f"PASSED: {result.tag_count} tags validated with {len(result.warnings)} warnings")
        else:
            print(f"FAILED: {len(result.errors)} errors, {len(result.warnings)} warnings in {result.tag_count} tags")

    if args.warnings_as_errors and result.warnings:
        return 1
    
    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
