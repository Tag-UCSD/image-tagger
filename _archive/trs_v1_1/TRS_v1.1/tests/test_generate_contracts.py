"""Tests for contract generation script."""

import json
import pytest
import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from generate_contracts import (
    generate_image_tagger_contract,
    generate_article_eater_contract,
    generate_bn_contract,
    generate_preference_testing_contract,
    generate_meta,
    sha256_file,
)


class TestContractGeneration:
    """Tests for contract generation functions."""

    def test_generate_meta(self):
        """Test metadata generation."""
        meta = generate_meta("abc123", "v1.0.0")
        
        assert meta["registry_sha256"] == "abc123"
        assert meta["contract_version"] == "v1.0.0"
        assert "generated_at_utc" in meta

    def test_image_tagger_contract_structure(self, sample_registry):
        """Test image tagger contract has correct structure."""
        tags = sample_registry["tags"]
        meta = generate_meta("test_sha", "v0.0.1")
        
        contract = generate_image_tagger_contract(tags, meta, "v0.0.1")
        
        assert "meta" in contract
        assert "contract_version" in contract
        assert "tags" in contract
        assert len(contract["tags"]) == 2
        
        # Check tag structure
        tag = contract["tags"][0]
        assert "tag_id" in tag
        assert "value_type" in tag
        assert "extractability" in tag
        assert "extraction" in tag

    def test_article_eater_contract_structure(self, sample_registry):
        """Test article eater contract has correct structure."""
        tags = sample_registry["tags"]
        meta = generate_meta("test_sha", "v0.0.1")
        
        contract = generate_article_eater_contract(tags, meta, "v0.0.1", sample_registry)
        
        assert "meta" in contract
        assert "source_registry" in contract
        assert "tags" in contract
        
        # Check tag structure
        tag = contract["tags"][0]
        assert "tag_id" in tag
        assert "status" in tag
        assert "search_terms" in tag
        assert "aliases" in tag

    def test_bn_contract_structure(self, sample_registry):
        """Test BN contract has correct structure."""
        tags = sample_registry["tags"]
        meta = generate_meta("test_sha", "v0.0.1")
        
        contract = generate_bn_contract(tags, meta, "v0.0.1")
        
        # Check tag structure
        tag = contract["tags"][0]
        assert "tag_id" in tag
        assert "bn" in tag
        assert "demand_state" in tag["bn"]
        assert "evidence_role" in tag["bn"]
        assert "consumable" in tag["bn"]

    def test_preference_testing_contract_structure(self, sample_registry):
        """Test preference testing contract has correct structure."""
        tags = sample_registry["tags"]
        meta = generate_meta("test_sha", "v0.0.1")
        
        contract = generate_preference_testing_contract(tags, meta, "v0.0.1")
        
        # Check tag structure
        tag = contract["tags"][0]
        assert "tag_id" in tag
        assert "value_type" in tag
        assert "definition" in tag

    def test_all_tags_included(self, sample_registry):
        """Test all tags from registry are included in contracts."""
        tags = sample_registry["tags"]
        meta = generate_meta("test_sha", "v0.0.1")
        
        contracts = [
            generate_image_tagger_contract(tags, meta, "v0.0.1"),
            generate_article_eater_contract(tags, meta, "v0.0.1", sample_registry),
            generate_bn_contract(tags, meta, "v0.0.1"),
            generate_preference_testing_contract(tags, meta, "v0.0.1"),
        ]
        
        for contract in contracts:
            assert len(contract["tags"]) == len(tags)


class TestRealRegistry:
    """Tests against the real registry."""

    def test_can_load_real_registry(self, registry_dir):
        """Test that the real registry can be loaded."""
        import yaml
        
        yamls = list(registry_dir.glob("*.yaml")) + list(registry_dir.glob("*.yml"))
        assert len(yamls) > 0, "No registry YAML found"
        
        registry = yaml.safe_load(yamls[0].read_text())
        assert "tags" in registry
        assert len(registry["tags"]) > 0

    def test_real_contracts_regenerate(self, registry_dir):
        """Test that contracts can be regenerated from real registry."""
        import yaml
        
        yamls = list(registry_dir.glob("*.yaml"))
        registry = yaml.safe_load(yamls[0].read_text())
        tags = registry["tags"]
        
        meta = generate_meta(sha256_file(yamls[0]), "v0.2.8")
        
        # Should not raise
        contract = generate_image_tagger_contract(tags, meta, "v0.2.8")
        assert len(contract["tags"]) == len(tags)
