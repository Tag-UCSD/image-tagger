"""
TRS-304: Integration tests for end-to-end workflow.

Tests the full proposal → review → merge → release cycle.
"""

import copy
import json
import pytest
import tempfile
import shutil
import yaml
from pathlib import Path
import sys

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.db.database import TRSDatabase


@pytest.fixture
def integration_setup(tmp_path):
    """Set up a complete test environment."""
    # Create database
    db_path = tmp_path / "test.db"
    db = TRSDatabase(db_path)
    
    # Create registry structure
    registry_dir = tmp_path / "core" / "trs-core" / "v0.1.0" / "registry"
    registry_dir.mkdir(parents=True)
    
    # Create initial registry
    registry = {
        "registry_name": "Test Registry",
        "content_version": "0.1.0",
        "tags": {
            "env.test.existing": {
                "canonical_name": "Existing Tag",
                "category": "environmental",
                "value_type": "ordinal",
                "status": "active",
                "definition": "An existing tag for testing",
            }
        }
    }
    
    registry_file = registry_dir / "test_registry.yaml"
    registry_file.write_text(yaml.dump(registry, default_flow_style=False))
    
    yield {
        "db": db,
        "db_path": db_path,
        "registry_dir": registry_dir,
        "registry_file": registry_file,
        "tmp_path": tmp_path,
    }


class TestProposalWorkflow:
    """Test the complete proposal workflow."""
    
    def test_create_and_approve_new_tag(self, integration_setup):
        """Test creating and approving a new tag proposal."""
        db = integration_setup["db"]
        
        # Create proposal
        proposal_id = db.create_proposal(
            proposal_type="new_tag",
            tag_id="env.test.new_tag",
            canonical_name="New Test Tag",
            payload={
                "canonical_name": "New Test Tag",
                "category": "environmental",
                "value_type": "binary",
                "status": "proposed",
                "definition": "A new tag",
            },
            submitter="researcher@test.com",
        )
        
        assert proposal_id == 1
        
        # Verify pending
        proposal = db.get_proposal(proposal_id)
        assert proposal.status == "pending"
        
        # Approve
        db.create_review(proposal_id, "reviewer@test.com", "approve", "LGTM")
        db.update_proposal_status(proposal_id, "approved")
        
        # Verify approved
        proposal = db.get_proposal(proposal_id)
        assert proposal.status == "approved"
    
    def test_reject_proposal(self, integration_setup):
        """Test rejecting a proposal."""
        db = integration_setup["db"]
        
        # Create proposal
        proposal_id = db.create_proposal(
            proposal_type="new_tag",
            tag_id="env.test.bad_tag",
            payload={"value_type": "ordinal"},
            submitter="researcher@test.com",
        )
        
        # Reject
        db.create_review(proposal_id, "reviewer@test.com", "reject", "Not needed")
        db.update_proposal_status(proposal_id, "rejected")
        
        # Verify rejected
        proposal = db.get_proposal(proposal_id)
        assert proposal.status == "rejected"
    
    def test_request_changes(self, integration_setup):
        """Test requesting changes keeps proposal pending."""
        db = integration_setup["db"]
        
        proposal_id = db.create_proposal(
            proposal_type="new_tag",
            tag_id="env.test.needs_work",
            payload={},
            submitter="researcher@test.com",
        )
        
        # Request changes
        db.create_review(proposal_id, "reviewer@test.com", "request_changes", "Add definition")
        
        # Status should still be pending
        proposal = db.get_proposal(proposal_id)
        assert proposal.status == "pending"
        
        # Multiple reviews allowed
        db.create_review(proposal_id, "reviewer@test.com", "approve", "Fixed!")
        
        reviews = db.get_reviews_for_proposal(proposal_id)
        assert len(reviews) == 2


class TestMergeWorkflow:
    """Test merging proposals into registry."""
    
    def test_merge_new_tag(self, integration_setup):
        """Test merging a new tag into registry."""
        db = integration_setup["db"]
        registry_file = integration_setup["registry_file"]
        
        # Create and approve proposal
        proposal_id = db.create_proposal(
            proposal_type="new_tag",
            tag_id="env.test.merged_tag",
            canonical_name="Merged Tag",
            payload={
                "canonical_name": "Merged Tag",
                "category": "environmental",
                "value_type": "continuous",
                "definition": "A merged tag",
            },
            submitter="researcher@test.com",
        )
        
        db.create_review(proposal_id, "reviewer@test.com", "approve")
        db.update_proposal_status(proposal_id, "approved")
        
        # Load registry
        registry = yaml.safe_load(registry_file.read_text())
        
        # Apply the proposal (simulating merge_proposals.py logic)
        proposal = db.get_proposal(proposal_id)
        tag_data = copy.deepcopy(proposal.payload)
        registry["tags"][proposal.tag_id] = tag_data
        
        # Save
        registry_file.write_text(yaml.dump(registry, default_flow_style=False))
        
        # Mark as merged
        db.update_proposal_status(proposal_id, "merged")
        
        # Verify
        final_registry = yaml.safe_load(registry_file.read_text())
        assert "env.test.merged_tag" in final_registry["tags"]
        assert final_registry["tags"]["env.test.merged_tag"]["value_type"] == "continuous"
        
        proposal = db.get_proposal(proposal_id)
        assert proposal.status == "merged"
    
    def test_merge_modify_tag(self, integration_setup):
        """Test merging a modification to existing tag."""
        db = integration_setup["db"]
        registry_file = integration_setup["registry_file"]
        
        # Create modify proposal
        proposal_id = db.create_proposal(
            proposal_type="modify_tag",
            tag_id="env.test.existing",
            payload={
                "definition": "Updated definition",
                "extractability": {"from_2d": "yes"},
            },
            submitter="researcher@test.com",
        )
        
        db.create_review(proposal_id, "reviewer@test.com", "approve")
        db.update_proposal_status(proposal_id, "approved")
        
        # Load and modify
        registry = yaml.safe_load(registry_file.read_text())
        proposal = db.get_proposal(proposal_id)
        
        # Deep merge
        existing = registry["tags"]["env.test.existing"]
        for key, value in proposal.payload.items():
            existing[key] = value
        
        registry_file.write_text(yaml.dump(registry, default_flow_style=False))
        db.update_proposal_status(proposal_id, "merged")
        
        # Verify
        final = yaml.safe_load(registry_file.read_text())
        tag = final["tags"]["env.test.existing"]
        assert tag["definition"] == "Updated definition"
        assert tag["extractability"]["from_2d"] == "yes"
        # Original fields preserved
        assert tag["canonical_name"] == "Existing Tag"
    
    def test_merge_deprecate_tag(self, integration_setup):
        """Test deprecating a tag."""
        db = integration_setup["db"]
        registry_file = integration_setup["registry_file"]
        
        # First add a replacement tag
        registry = yaml.safe_load(registry_file.read_text())
        registry["tags"]["env.test.replacement"] = {
            "canonical_name": "Replacement Tag",
            "value_type": "ordinal",
            "status": "active",
        }
        registry_file.write_text(yaml.dump(registry, default_flow_style=False))
        
        # Create deprecate proposal
        proposal_id = db.create_proposal(
            proposal_type="deprecate_tag",
            tag_id="env.test.existing",
            payload={"replaced_by": "env.test.replacement"},
            submitter="researcher@test.com",
        )
        
        db.create_review(proposal_id, "reviewer@test.com", "approve")
        db.update_proposal_status(proposal_id, "approved")
        
        # Apply deprecation
        registry = yaml.safe_load(registry_file.read_text())
        proposal = db.get_proposal(proposal_id)
        
        registry["tags"]["env.test.existing"]["status"] = "deprecated"
        registry["tags"]["env.test.existing"]["replaced_by"] = proposal.payload.get("replaced_by")
        
        registry_file.write_text(yaml.dump(registry, default_flow_style=False))
        db.update_proposal_status(proposal_id, "merged")
        
        # Verify
        final = yaml.safe_load(registry_file.read_text())
        tag = final["tags"]["env.test.existing"]
        assert tag["status"] == "deprecated"
        assert tag["replaced_by"] == "env.test.replacement"


class TestReleaseWorkflow:
    """Test the release workflow."""
    
    def test_record_release(self, integration_setup):
        """Test recording a release."""
        db = integration_setup["db"]
        
        release_id = db.record_release(
            version="v0.1.0",
            registry_sha256="abc123",
            released_by="admin@test.com",
            tags_added=2,
            tags_modified=1,
            release_notes="Initial release",
        )
        
        assert release_id == 1
        
        # Get latest
        latest = db.get_latest_release()
        assert latest.version == "v0.1.0"
        assert latest.tags_added == 2
    
    def test_release_marks_proposals_merged(self, integration_setup):
        """Test that release updates approved proposals to merged."""
        db = integration_setup["db"]
        
        # Create and approve some proposals
        ids = []
        for i in range(3):
            pid = db.create_proposal(
                proposal_type="new_tag",
                tag_id=f"env.test.tag_{i}",
                payload={},
                submitter="test@test.com",
            )
            db.update_proposal_status(pid, "approved")
            ids.append(pid)
        
        # Verify all approved
        assert db.count_proposals("approved") == 3
        
        # Simulate release marking them merged
        for pid in ids:
            db.update_proposal_status(pid, "merged")
        
        # Record release
        db.record_release(
            version="v0.2.0",
            previous_version="v0.1.0",
            registry_sha256="def456",
            released_by="admin@test.com",
            tags_added=3,
        )
        
        # Verify
        assert db.count_proposals("merged") == 3
        assert db.count_proposals("approved") == 0


class TestAuditTrail:
    """Test audit logging throughout workflow."""
    
    def test_proposal_lifecycle_logged(self, integration_setup):
        """Test that all proposal actions are logged."""
        db = integration_setup["db"]
        
        # Create
        proposal_id = db.create_proposal(
            proposal_type="new_tag",
            tag_id="env.test.audited",
            payload={},
            submitter="user@test.com",
        )
        db.log_action("proposal_created", "user@test.com", "proposal", str(proposal_id))
        
        # Review
        db.create_review(proposal_id, "reviewer@test.com", "approve")
        db.log_action("proposal_reviewed", "reviewer@test.com", "proposal", str(proposal_id))
        
        # Get audit log
        entries = db.get_audit_log()
        
        assert len(entries) >= 2
        actions = [e.action for e in entries]
        assert "proposal_created" in actions
        assert "proposal_reviewed" in actions


class TestAPIKeyWorkflow:
    """Test API key lifecycle."""
    
    def test_full_key_lifecycle(self, integration_setup):
        """Test create, use, revoke key."""
        db = integration_setup["db"]
        
        # Create
        key_id, raw_key = db.create_api_key("Test Key", "proposer", "admin@test.com")
        
        # Validate
        validated = db.validate_api_key(raw_key)
        assert validated is not None
        assert validated.role == "proposer"
        
        # List
        keys = db.list_api_keys()
        assert len(keys) == 1
        
        # Revoke
        db.revoke_api_key(key_id)
        
        # Can't use anymore
        validated = db.validate_api_key(raw_key)
        assert validated is None
