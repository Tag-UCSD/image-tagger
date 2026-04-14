"""Tests for registry diff and breaking change detection."""

import pytest
import sys
import yaml
import tempfile
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from diff_registry import diff_registries, DiffResult


def write_registry(path: Path, registry: dict) -> None:
    """Write a registry dict to a YAML file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.dump(registry, default_flow_style=False, allow_unicode=True),
        encoding="utf-8"
    )


class TestDiffDetection:
    """Tests for change detection."""

    def test_identical_registries_no_changes(self, sample_registry, tmp_path):
        """Test that identical registries show no changes."""
        old_path = tmp_path / "old" / "registry.yaml"
        new_path = tmp_path / "new" / "registry.yaml"
        
        write_registry(old_path, sample_registry)
        write_registry(new_path, sample_registry)
        
        result = diff_registries(old_path.parent, new_path.parent)
        
        assert not result.has_breaking
        assert len(result.changes) == 0

    def test_removed_tag_is_breaking(self, sample_registry, registry_with_removed_tag, tmp_path):
        """Test that removed tags are detected as breaking changes."""
        old_path = tmp_path / "old" / "registry.yaml"
        new_path = tmp_path / "new" / "registry.yaml"
        
        write_registry(old_path, sample_registry)
        write_registry(new_path, registry_with_removed_tag)
        
        result = diff_registries(old_path.parent, new_path.parent)
        
        assert result.has_breaking
        assert any(c.change_type == "TAG_REMOVED" for c in result.breaking_changes)

    def test_value_type_change_is_breaking(self, sample_registry, registry_with_type_change, tmp_path):
        """Test that value_type changes are detected as breaking."""
        old_path = tmp_path / "old" / "registry.yaml"
        new_path = tmp_path / "new" / "registry.yaml"
        
        write_registry(old_path, sample_registry)
        write_registry(new_path, registry_with_type_change)
        
        result = diff_registries(old_path.parent, new_path.parent)
        
        assert result.has_breaking
        assert any(c.change_type == "VALUE_TYPE_CHANGED" for c in result.breaking_changes)

    def test_new_tag_is_info(self, sample_registry, registry_with_new_tag, tmp_path):
        """Test that new tags are detected as info (not breaking)."""
        old_path = tmp_path / "old" / "registry.yaml"
        new_path = tmp_path / "new" / "registry.yaml"
        
        write_registry(old_path, sample_registry)
        write_registry(new_path, registry_with_new_tag)
        
        result = diff_registries(old_path.parent, new_path.parent)
        
        assert not result.has_breaking
        assert any(c.change_type == "TAG_ADDED" for c in result.info)

    def test_deprecation_is_warning(self, sample_registry, tmp_path):
        """Test that deprecation is a warning, not breaking."""
        import copy
        
        old_path = tmp_path / "old" / "registry.yaml"
        new_path = tmp_path / "new" / "registry.yaml"
        
        # Create version with deprecated tag
        deprecated_registry = copy.deepcopy(sample_registry)
        deprecated_registry["tags"]["env.test.tag_one"]["status"] = "deprecated"
        
        write_registry(old_path, sample_registry)
        write_registry(new_path, deprecated_registry)
        
        result = diff_registries(old_path.parent, new_path.parent)
        
        assert not result.has_breaking
        assert any(c.change_type == "TAG_DEPRECATED" for c in result.warnings)


class TestDiffResult:
    """Tests for DiffResult class."""

    def test_to_dict_structure(self):
        """Test that to_dict produces expected structure."""
        result = DiffResult(old_version="v1", new_version="v2")
        
        d = result.to_dict()
        
        assert "old_version" in d
        assert "new_version" in d
        assert "has_breaking_changes" in d
        assert "summary" in d
        assert "changes" in d

    def test_has_breaking_property(self):
        """Test has_breaking property works correctly."""
        from diff_registry import Change
        
        result = DiffResult(old_version="v1", new_version="v2")
        assert not result.has_breaking
        
        result.changes.append(Change(
            severity="BREAKING",
            change_type="TEST",
            tag_id="test",
            details="test"
        ))
        assert result.has_breaking
