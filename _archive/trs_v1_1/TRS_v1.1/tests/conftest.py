"""Pytest configuration and shared fixtures for TRS tests."""

import pytest
import yaml
from pathlib import Path
import tempfile
import shutil


@pytest.fixture
def repo_root() -> Path:
    """Get the repository root directory."""
    return Path(__file__).resolve().parent.parent


@pytest.fixture
def registry_dir(repo_root) -> Path:
    """Get the current registry directory."""
    return repo_root / "core" / "trs-core" / "v0.2.8" / "registry"


@pytest.fixture
def sample_registry() -> dict:
    """Create a minimal valid registry for testing."""
    return {
        "registry_name": "Test Registry",
        "registry_format_version": "1.0.0",
        "content_version": "0.0.1",
        "tags": {
            "env.test.tag_one": {
                "canonical_name": "Test Tag One",
                "category": "environmental",
                "value_type": "ordinal",
                "status": "active",
                "definition": "A test tag for validation",
                "domain": "Test Domain",
                "extractability": {
                    "from_2d": "yes",
                    "from_3d_vr": "partial",
                },
                "bn": {
                    "demand_state": "optional",
                    "evidence_role": "stimulus_antecedent",
                    "consumable": True,
                },
                "semantics": {
                    "aliases": ["tag one", "first tag"],
                },
                "literature": {
                    "search_terms": ["test tag"],
                },
            },
            "env.test.tag_two": {
                "canonical_name": "Test Tag Two",
                "category": "environmental",
                "value_type": "binary",
                "status": "active",
                "definition": "Another test tag",
                "domain": "Test Domain",
                "extractability": {
                    "from_2d": "partial",
                },
                "bn": {
                    "demand_state": "required",
                    "evidence_role": "stimulus_antecedent",
                    "consumable": True,
                },
                "semantics": {
                    "aliases": ["tag two", "second tag"],
                },
            },
        },
    }


@pytest.fixture
def temp_registry_dir(sample_registry) -> Path:
    """Create a temporary registry directory with sample data."""
    temp_dir = Path(tempfile.mkdtemp())
    registry_file = temp_dir / "test_registry.yaml"
    registry_file.write_text(
        yaml.dump(sample_registry, default_flow_style=False, allow_unicode=True),
        encoding="utf-8"
    )
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def invalid_registry_with_duplicate_alias(sample_registry) -> dict:
    """Create a registry with duplicate aliases (validation should fail)."""
    import copy
    registry = copy.deepcopy(sample_registry)
    # Add duplicate alias
    registry["tags"]["env.test.tag_two"]["semantics"]["aliases"].append("tag one")  # Duplicate!
    return registry


@pytest.fixture
def invalid_registry_with_orphan_parent(sample_registry) -> dict:
    """Create a registry with orphan parent reference."""
    import copy
    registry = copy.deepcopy(sample_registry)
    registry["tags"]["env.test.tag_one"]["semantics"]["hierarchy"] = {
        "parent": "env.nonexistent.parent"  # Doesn't exist
    }
    return registry


@pytest.fixture
def registry_with_removed_tag(sample_registry) -> dict:
    """Create a registry with one tag removed (for diff testing)."""
    import copy
    registry = copy.deepcopy(sample_registry)
    del registry["tags"]["env.test.tag_one"]
    return registry


@pytest.fixture
def registry_with_type_change(sample_registry) -> dict:
    """Create a registry with value_type changed (breaking change)."""
    import copy
    registry = copy.deepcopy(sample_registry)
    registry["tags"]["env.test.tag_one"]["value_type"] = "continuous"  # Was ordinal
    return registry


@pytest.fixture
def registry_with_new_tag(sample_registry) -> dict:
    """Create a registry with a new tag added."""
    import copy
    registry = copy.deepcopy(sample_registry)
    registry["tags"]["env.test.tag_three"] = {
        "canonical_name": "Test Tag Three",
        "category": "environmental",
        "value_type": "continuous",
        "status": "active",
        "definition": "A new test tag",
    }
    return registry
