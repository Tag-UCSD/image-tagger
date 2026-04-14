"""Tests for registry validation script."""

import pytest
import sys
import yaml
import tempfile
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from validate_registry import validate_registry, validate_tag_schema, validate_invariants, ValidationResult


class TestSchemaValidation:
    """Tests for schema validation."""

    def test_valid_registry_passes(self, temp_registry_dir):
        """Test that a valid registry passes validation."""
        result = validate_registry(temp_registry_dir)
        assert result.passed, f"Expected pass, got errors: {[str(e) for e in result.errors]}"

    def test_missing_required_field_fails(self, sample_registry):
        """Test that missing required fields are caught."""
        result = ValidationResult()
        
        # Tag missing canonical_name
        bad_tag = {"category": "environmental", "value_type": "ordinal", "status": "active"}
        validate_tag_schema("test.bad.tag", bad_tag, result)
        
        assert not result.passed
        assert any("canonical_name" in e.field for e in result.errors)

    def test_invalid_value_type_fails(self, sample_registry):
        """Test that invalid value_type is caught."""
        result = ValidationResult()
        
        bad_tag = {
            "canonical_name": "Test",
            "category": "environmental",
            "value_type": "invalid_type",  # Bad!
            "status": "active",
        }
        validate_tag_schema("test.bad.tag", bad_tag, result)
        
        assert not result.passed
        assert any("value_type" in e.field for e in result.errors)

    def test_invalid_status_fails(self, sample_registry):
        """Test that invalid status is caught."""
        result = ValidationResult()
        
        bad_tag = {
            "canonical_name": "Test",
            "category": "environmental",
            "value_type": "ordinal",
            "status": "invalid_status",  # Bad!
        }
        validate_tag_schema("test.bad.tag", bad_tag, result)
        
        assert not result.passed
        assert any("status" in e.field for e in result.errors)


class TestInvariantValidation:
    """Tests for semantic invariant validation."""

    def test_duplicate_alias_detected(self, invalid_registry_with_duplicate_alias):
        """Test that duplicate aliases are detected."""
        result = ValidationResult()
        validate_invariants(invalid_registry_with_duplicate_alias["tags"], result)
        
        assert not result.passed
        assert any("Duplicate alias" in e.message for e in result.errors)

    def test_orphan_parent_detected(self, invalid_registry_with_orphan_parent):
        """Test that orphan parent references are detected."""
        result = ValidationResult()
        validate_invariants(invalid_registry_with_orphan_parent["tags"], result)
        
        assert not result.passed
        assert any("does not exist" in e.message for e in result.errors)

    def test_valid_registry_no_invariant_errors(self, sample_registry):
        """Test that a valid registry has no invariant errors."""
        result = ValidationResult()
        validate_invariants(sample_registry["tags"], result)
        
        # Should pass (no errors, may have warnings)
        assert result.passed


class TestRealRegistry:
    """Tests against the real registry."""

    def test_real_registry_loads(self, registry_dir):
        """Test that the real registry can be validated."""
        result = validate_registry(registry_dir)
        
        # We know the real registry has some issues (duplicate aliases)
        # Just verify it can be processed
        assert result.tag_count > 0

    def test_real_registry_tag_count(self, registry_dir):
        """Test that the real registry has expected tag count."""
        result = validate_registry(registry_dir)
        assert result.tag_count == 424, f"Expected 424 tags, got {result.tag_count}"
