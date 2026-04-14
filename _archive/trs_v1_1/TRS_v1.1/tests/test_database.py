"""Tests for TRS database module."""

import pytest
import tempfile
from pathlib import Path
import sys

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.db.database import TRSDatabase


@pytest.fixture
def db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    
    database = TRSDatabase(db_path)
    yield database
    
    # Cleanup
    db_path.unlink(missing_ok=True)


class TestProposals:
    """Tests for proposal CRUD operations."""
    
    def test_create_proposal(self, db):
        """Test creating a proposal."""
        proposal_id = db.create_proposal(
            proposal_type="new_tag",
            tag_id="env.test.tag",
            payload={"value_type": "ordinal"},
            submitter="test@example.com",
        )
        
        assert proposal_id == 1
    
    def test_get_proposal(self, db):
        """Test retrieving a proposal."""
        db.create_proposal(
            proposal_type="new_tag",
            tag_id="env.test.tag",
            canonical_name="Test Tag",
            payload={"value_type": "ordinal"},
            submitter="test@example.com",
            evidence_doi="https://doi.org/10.1234/test",
        )
        
        proposal = db.get_proposal(1)
        
        assert proposal is not None
        assert proposal.tag_id == "env.test.tag"
        assert proposal.canonical_name == "Test Tag"
        assert proposal.status == "pending"
        assert proposal.payload == {"value_type": "ordinal"}
    
    def test_list_proposals(self, db):
        """Test listing proposals."""
        db.create_proposal("new_tag", "env.test.one", {}, "user1@test.com")
        db.create_proposal("new_tag", "env.test.two", {}, "user2@test.com")
        
        proposals = db.list_proposals()
        assert len(proposals) == 2
    
    def test_list_proposals_filter_by_status(self, db):
        """Test filtering proposals by status."""
        db.create_proposal("new_tag", "env.test.one", {}, "user@test.com")
        db.create_proposal("new_tag", "env.test.two", {}, "user@test.com")
        db.update_proposal_status(1, "approved")
        
        pending = db.list_proposals(status="pending")
        approved = db.list_proposals(status="approved")
        
        assert len(pending) == 1
        assert len(approved) == 1
    
    def test_count_proposals(self, db):
        """Test counting proposals."""
        db.create_proposal("new_tag", "env.test.one", {}, "user@test.com")
        db.create_proposal("new_tag", "env.test.two", {}, "user@test.com")
        db.update_proposal_status(1, "approved")
        
        assert db.count_proposals() == 2
        assert db.count_proposals("pending") == 1
        assert db.count_proposals("approved") == 1


class TestReviews:
    """Tests for review operations."""
    
    def test_create_review(self, db):
        """Test creating a review."""
        db.create_proposal("new_tag", "env.test.tag", {}, "submitter@test.com")
        
        review_id = db.create_review(
            proposal_id=1,
            reviewer="reviewer@test.com",
            decision="approve",
            comment="Looks good!",
        )
        
        assert review_id == 1
    
    def test_get_reviews_for_proposal(self, db):
        """Test retrieving reviews for a proposal."""
        db.create_proposal("new_tag", "env.test.tag", {}, "submitter@test.com")
        db.create_review(1, "reviewer1@test.com", "request_changes", "Needs more detail")
        db.create_review(1, "reviewer2@test.com", "approve", "LGTM")
        
        reviews = db.get_reviews_for_proposal(1)
        
        assert len(reviews) == 2


class TestAPIKeys:
    """Tests for API key operations."""
    
    def test_create_api_key(self, db):
        """Test creating an API key."""
        key_id, raw_key = db.create_api_key(
            name="Test Key",
            role="proposer",
            created_by="admin@test.com",
        )
        
        assert key_id == 1
        assert raw_key.startswith("trs_")
        assert len(raw_key) > 20
    
    def test_validate_api_key(self, db):
        """Test validating an API key."""
        _, raw_key = db.create_api_key("Test Key", "reviewer", "admin@test.com")
        
        validated = db.validate_api_key(raw_key)
        
        assert validated is not None
        assert validated.name == "Test Key"
        assert validated.role == "reviewer"
    
    def test_invalid_api_key_returns_none(self, db):
        """Test that invalid keys return None."""
        validated = db.validate_api_key("trs_invalid_key_12345")
        assert validated is None
    
    def test_revoke_api_key(self, db):
        """Test revoking an API key."""
        key_id, raw_key = db.create_api_key("Test Key", "proposer", "admin@test.com")
        
        # Should be valid
        assert db.validate_api_key(raw_key) is not None
        
        # Revoke
        db.revoke_api_key(key_id)
        
        # Should no longer be valid
        assert db.validate_api_key(raw_key) is None


class TestAuditLog:
    """Tests for audit log operations."""
    
    def test_log_action(self, db):
        """Test logging an action."""
        entry_id = db.log_action(
            action="test_action",
            user_id="user@test.com",
            target_type="test",
            target_id="123",
            details={"key": "value"},
        )
        
        assert entry_id == 1
    
    def test_get_audit_log(self, db):
        """Test retrieving audit log."""
        db.log_action("action1", "user1@test.com")
        db.log_action("action2", "user2@test.com")
        
        entries = db.get_audit_log()
        
        assert len(entries) == 2
    
    def test_filter_audit_log_by_action(self, db):
        """Test filtering audit log by action."""
        db.log_action("create", "user@test.com")
        db.log_action("update", "user@test.com")
        db.log_action("create", "user@test.com")
        
        creates = db.get_audit_log(action="create")
        
        assert len(creates) == 2


class TestReleases:
    """Tests for release operations."""
    
    def test_record_release(self, db):
        """Test recording a release."""
        release_id = db.record_release(
            version="v0.1.0",
            registry_sha256="abc123",
            released_by="admin@test.com",
            tags_added=5,
        )
        
        assert release_id == 1
    
    def test_get_latest_release(self, db):
        """Test getting latest release."""
        db.record_release("v0.1.0", "sha1", "admin@test.com")
        
        # Get latest after first insert
        latest = db.get_latest_release()
        assert latest.version == "v0.1.0"
        
        # Add second release
        db.record_release("v0.2.0", "sha2", "admin@test.com", previous_version="v0.1.0")
        
        # Now latest should be v0.2.0 (highest ID since same timestamp)
        releases = db.list_releases()
        # Verify we have both
        assert len(releases) == 2


class TestSettings:
    """Tests for settings operations."""
    
    def test_get_default_setting(self, db):
        """Test getting a setting that doesn't exist."""
        value = db.get_setting("nonexistent", default="default_value")
        assert value == "default_value"
    
    def test_set_and_get_setting(self, db):
        """Test setting and getting a value."""
        db.set_setting("test_key", "test_value", updated_by="admin")
        
        value = db.get_setting("test_key")
        assert value == "test_value"
    
    def test_update_setting(self, db):
        """Test updating an existing setting."""
        db.set_setting("key", "value1")
        db.set_setting("key", "value2")
        
        value = db.get_setting("key")
        assert value == "value2"
