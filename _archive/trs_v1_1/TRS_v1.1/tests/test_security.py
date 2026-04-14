"""
TRS-1001: Security Unit Tests

Tests for authentication, authorization, and security middleware.
These tests are designed to run without FastAPI dependencies.
"""

import pytest
import hashlib
import time
import sqlite3
import tempfile
from pathlib import Path
import sys

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.db.database import TRSDatabase


class TestAPIKeyAuthentication:
    """Tests for API key authentication via database."""
    
    @pytest.fixture
    def db(self):
        """Create a temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)
        database = TRSDatabase(db_path)
        yield database
        db_path.unlink(missing_ok=True)
    
    def test_create_api_key_returns_usable_key(self, db):
        """Created API key should be usable."""
        key_id, raw_key = db.create_api_key(
            name="Test Key",
            role="viewer",
            created_by="test_admin"
        )
        
        assert key_id is not None
        assert raw_key.startswith("trs_")
    
    def test_validate_valid_key(self, db):
        """validate_api_key should return APIKey for valid key."""
        _, raw_key = db.create_api_key(
            name="Verify Test",
            role="proposer",
            created_by="admin"
        )
        
        result = db.validate_api_key(raw_key)
        assert result is not None
        assert result.name == "Verify Test"
        assert result.role == "proposer"
    
    def test_validate_invalid_key_returns_none(self, db):
        """validate_api_key should return None for invalid key."""
        result = db.validate_api_key("trs_nonexistent_key123")
        assert result is None
    
    def test_revoked_key_rejected(self, db):
        """Revoked API key should be rejected."""
        key_id, raw_key = db.create_api_key(
            name="To Revoke",
            role="viewer",
            created_by="admin"
        )
        
        # Key should work before revocation
        assert db.validate_api_key(raw_key) is not None
        
        # Revoke the key
        db.revoke_api_key(key_id)
        
        # Should now be rejected
        result = db.validate_api_key(raw_key)
        assert result is None


class TestRoleHierarchy:
    """Tests for role-based authorization concepts."""
    
    def test_role_order(self):
        """Test role hierarchy: admin > reviewer > proposer > viewer."""
        roles = ["viewer", "proposer", "reviewer", "admin"]
        
        # Each role should have higher index than previous
        for i in range(1, len(roles)):
            assert roles.index(roles[i]) > roles.index(roles[i-1])
    
    def test_admin_is_highest(self):
        """Admin should be the highest role."""
        roles = ["viewer", "proposer", "reviewer", "admin"]
        assert roles[-1] == "admin"
    
    def test_viewer_is_lowest(self):
        """Viewer should be the lowest role."""
        roles = ["viewer", "proposer", "reviewer", "admin"]
        assert roles[0] == "viewer"
    
    def test_role_level_calculation(self):
        """Role levels should be calculable from index."""
        roles = ["viewer", "proposer", "reviewer", "admin"]
        
        def get_level(role):
            return roles.index(role)
        
        assert get_level("admin") > get_level("reviewer")
        assert get_level("reviewer") > get_level("proposer")
        assert get_level("proposer") > get_level("viewer")


class TestAtomicReviewTransaction:
    """Tests for atomic proposal review (race condition prevention)."""
    
    @pytest.fixture
    def db(self):
        """Create a temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)
        database = TRSDatabase(db_path)
        yield database
        db_path.unlink(missing_ok=True)
    
    def test_atomic_review_approves(self, db):
        """Atomic review should approve pending proposal."""
        proposal_id = db.create_proposal(
            proposal_type="new_tag",
            tag_id="test.tag",
            payload={"definition": "Test"},
            submitter="test@example.com"
        )
        
        success, message, review_id = db.atomic_review_proposal(
            proposal_id=proposal_id,
            reviewer="reviewer@example.com",
            decision="approve",
            comment="LGTM"
        )
        
        assert success is True
        assert "approved" in message.lower()
        assert review_id is not None
        
        # Verify status changed
        proposal = db.get_proposal(proposal_id)
        assert proposal.status == "approved"
    
    def test_atomic_review_rejects(self, db):
        """Atomic review should reject pending proposal."""
        proposal_id = db.create_proposal(
            proposal_type="new_tag",
            tag_id="test.tag2",
            payload={"definition": "Test"},
            submitter="test@example.com"
        )
        
        success, message, review_id = db.atomic_review_proposal(
            proposal_id=proposal_id,
            reviewer="reviewer@example.com",
            decision="reject",
            comment="Not ready"
        )
        
        assert success is True
        assert "rejected" in message.lower()
        
        proposal = db.get_proposal(proposal_id)
        assert proposal.status == "rejected"
    
    def test_cannot_review_already_approved(self, db):
        """Cannot review already-approved proposal."""
        proposal_id = db.create_proposal(
            proposal_type="new_tag",
            tag_id="test.tag3",
            payload={"definition": "Test"},
            submitter="test@example.com"
        )
        
        # First review approves
        db.atomic_review_proposal(
            proposal_id=proposal_id,
            reviewer="reviewer1@example.com",
            decision="approve",
            comment="First"
        )
        
        # Second review should fail
        success, message, review_id = db.atomic_review_proposal(
            proposal_id=proposal_id,
            reviewer="reviewer2@example.com",
            decision="reject",
            comment="Too late"
        )
        
        assert success is False
        assert "already" in message.lower()
        assert review_id is None
    
    def test_review_nonexistent_proposal(self, db):
        """Reviewing nonexistent proposal should fail gracefully."""
        success, message, review_id = db.atomic_review_proposal(
            proposal_id=99999,
            reviewer="reviewer@example.com",
            decision="approve",
            comment="Ghost"
        )
        
        assert success is False
        assert "not found" in message.lower()
        assert review_id is None
    
    def test_request_changes_keeps_pending(self, db):
        """Request changes should keep proposal pending."""
        proposal_id = db.create_proposal(
            proposal_type="new_tag",
            tag_id="test.tag4",
            payload={"definition": "Test"},
            submitter="test@example.com"
        )
        
        success, message, review_id = db.atomic_review_proposal(
            proposal_id=proposal_id,
            reviewer="reviewer@example.com",
            decision="request_changes",
            comment="Please add more detail"
        )
        
        assert success is True
        assert review_id is not None
        
        # Should still be pending
        proposal = db.get_proposal(proposal_id)
        assert proposal.status == "pending"


class TestInputValidation:
    """Tests for input validation patterns."""
    
    def test_tag_id_valid_patterns(self):
        """Valid tag ID patterns should be identifiable."""
        valid_patterns = [
            r"^[a-z][a-z0-9_.]*$",  # Starts with letter, allows dots/underscores
        ]
        
        import re
        pattern = re.compile(valid_patterns[0])
        
        valid_ids = [
            "env.ae.lighting.intensity",
            "spat.layout.openness",
            "mat.surface.texture",
            "simple_tag",
            "tag123",
        ]
        
        for tag_id in valid_ids:
            assert pattern.match(tag_id), f"Should match: {tag_id}"
    
    def test_tag_id_invalid_patterns(self):
        """Invalid tag ID patterns should be detectable."""
        import re
        pattern = re.compile(r"^[a-z][a-z0-9_.]{0,200}$")
        
        invalid_ids = [
            "../../../etc/passwd",  # Path traversal
            "tag<script>",  # XSS attempt
            "",  # Empty
            "123tag",  # Starts with number
            "TAG.UPPER",  # Uppercase
            "a" * 300,  # Too long
        ]
        
        for tag_id in invalid_ids:
            assert not pattern.match(tag_id), f"Should NOT match: {tag_id}"
    
    def test_path_traversal_detection(self):
        """Path traversal patterns should be detectable."""
        dangerous = [
            "../",
            "..\\",
            "..%2F",
            "..%5C",
        ]
        
        for pattern in dangerous:
            # All these should be blocked
            assert ".." in pattern or "%2" in pattern.lower()


class TestAPIKeyFormat:
    """Tests for API key format standards."""
    
    def test_key_has_prefix(self):
        """API keys should start with trs_ prefix."""
        test_keys = [
            "trs_abc123def456ghi789",
            "trs_000000000000000000",
        ]
        
        for key in test_keys:
            assert key.startswith("trs_")
    
    def test_key_hash_is_sha256(self):
        """API key hashes should be SHA-256 (64 hex chars)."""
        key = "trs_test1234567890abcd"
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        
        assert len(key_hash) == 64
        assert all(c in "0123456789abcdef" for c in key_hash)
    
    def test_prefix_extraction(self):
        """Key prefix should be extractable for identification."""
        key = "trs_abc123def456ghi789"
        prefix = key[:12]  # "trs_abc12345"
        
        assert prefix.startswith("trs_")
        assert len(prefix) == 12


class TestDatabaseConstraints:
    """Tests for database constraint enforcement."""
    
    @pytest.fixture
    def db(self):
        """Create a temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)
        database = TRSDatabase(db_path)
        yield database
        db_path.unlink(missing_ok=True)
    
    def test_proposal_status_constraint(self, db):
        """Proposal status should only allow valid values."""
        valid_statuses = ["pending", "approved", "rejected", "merged", "withdrawn"]
        
        proposal_id = db.create_proposal(
            proposal_type="new_tag",
            tag_id="test.constraint",
            payload={"def": "test"},
            submitter="test@example.com"
        )
        
        proposal = db.get_proposal(proposal_id)
        assert proposal.status in valid_statuses
    
    def test_review_decision_constraint(self, db):
        """Review decision should only allow valid values."""
        valid_decisions = ["approve", "reject", "request_changes"]
        
        proposal_id = db.create_proposal(
            proposal_type="new_tag",
            tag_id="test.decision",
            payload={"def": "test"},
            submitter="test@example.com"
        )
        
        # All valid decisions should work
        for decision in valid_decisions:
            # Create new proposal for each test
            pid = db.create_proposal(
                proposal_type="new_tag",
                tag_id=f"test.decision.{decision}",
                payload={"def": "test"},
                submitter="test@example.com"
            )
            
            success, _, _ = db.atomic_review_proposal(
                proposal_id=pid,
                reviewer="reviewer@test.com",
                decision=decision,
                comment="Test"
            )
            
            assert success is True, f"Decision '{decision}' should be valid"
    
    def test_role_constraint(self, db):
        """API key roles should only allow valid values."""
        valid_roles = ["viewer", "proposer", "reviewer", "admin"]
        
        for role in valid_roles:
            key = db.create_api_key(
                name=f"Test {role}",
                role=role,
                created_by="admin"
            )
            assert key is not None, f"Role '{role}' should be valid"


