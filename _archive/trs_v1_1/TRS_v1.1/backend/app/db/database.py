"""
TRS-202: Database module for TRS persistence.

Provides CRUD operations for proposals, reviews, releases, audit logs, and API keys.
Uses SQLite with WAL mode for concurrent access.

Usage:
    from backend.app.db.database import get_db, TRSDatabase
    
    db = get_db()
    proposal_id = db.create_proposal(...)
    proposals = db.list_proposals(status='pending')
"""

from __future__ import annotations
import hashlib
import json
import secrets
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class Proposal:
    id: int
    proposal_type: str
    tag_id: str
    canonical_name: Optional[str]
    payload: dict
    evidence_doi: Optional[str]
    reason: Optional[str]
    status: str
    submitter: str
    created_at: str
    updated_at: str


@dataclass
class Review:
    id: int
    proposal_id: int
    reviewer: str
    decision: str
    comment: Optional[str]
    created_at: str


@dataclass
class Release:
    id: int
    version: str
    previous_version: Optional[str]
    registry_sha256: str
    tags_added: int
    tags_removed: int
    tags_modified: int
    released_by: str
    release_notes: Optional[str]
    created_at: str


@dataclass
class APIKey:
    id: int
    key_prefix: str
    name: str
    role: str
    created_by: str
    created_at: str
    last_used_at: Optional[str]
    expires_at: Optional[str]
    revoked_at: Optional[str]
    
    @property
    def is_active(self) -> bool:
        if self.revoked_at:
            return False
        if self.expires_at:
            expires = datetime.fromisoformat(self.expires_at.replace('Z', '+00:00'))
            if expires < datetime.now(timezone.utc):
                return False
        return True


@dataclass
class AuditEntry:
    id: int
    timestamp: str
    action: str
    user_id: str
    target_type: Optional[str]
    target_id: Optional[str]
    details: Optional[dict]
    ip_address: Optional[str]


# ============================================================================
# Database Class
# ============================================================================

class TRSDatabase:
    """SQLite database wrapper for TRS."""
    
    def __init__(self, db_path: str | Path = "trs.db"):
        self.db_path = Path(db_path)
        self._ensure_schema()
    
    def _ensure_schema(self) -> None:
        """Create tables if they don't exist."""
        schema_path = Path(__file__).parent / "schema.sql"
        if schema_path.exists():
            schema_sql = schema_path.read_text()
        else:
            # Inline minimal schema if file not found
            schema_sql = self._get_inline_schema()
        
        with self._connect() as conn:
            conn.executescript(schema_sql)
    
    def _get_inline_schema(self) -> str:
        """Fallback inline schema."""
        return """
        PRAGMA journal_mode = WAL;
        PRAGMA foreign_keys = ON;
        
        CREATE TABLE IF NOT EXISTS proposals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proposal_type TEXT NOT NULL,
            tag_id TEXT NOT NULL,
            canonical_name TEXT,
            payload TEXT NOT NULL,
            evidence_doi TEXT,
            reason TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            submitter TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proposal_id INTEGER NOT NULL REFERENCES proposals(id),
            reviewer TEXT NOT NULL,
            decision TEXT NOT NULL,
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS releases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version TEXT NOT NULL UNIQUE,
            previous_version TEXT,
            registry_sha256 TEXT NOT NULL,
            tags_added INTEGER DEFAULT 0,
            tags_removed INTEGER DEFAULT 0,
            tags_modified INTEGER DEFAULT 0,
            released_by TEXT NOT NULL,
            release_notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            action TEXT NOT NULL,
            user_id TEXT NOT NULL,
            target_type TEXT,
            target_id TEXT,
            details TEXT,
            ip_address TEXT,
            user_agent TEXT
        );
        
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key_hash TEXT NOT NULL UNIQUE,
            key_prefix TEXT NOT NULL,
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            created_by TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used_at TIMESTAMP,
            expires_at TIMESTAMP,
            revoked_at TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_by TEXT
        );
        """
    
    @contextmanager
    def _connect(self):
        """Get a database connection with row factory."""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    # ========================================================================
    # Proposals
    # ========================================================================
    
    def create_proposal(
        self,
        proposal_type: str,
        tag_id: str,
        payload: dict,
        submitter: str,
        canonical_name: Optional[str] = None,
        evidence_doi: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> int:
        """Create a new proposal. Returns proposal ID."""
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO proposals (proposal_type, tag_id, canonical_name, payload, evidence_doi, reason, submitter)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (proposal_type, tag_id, canonical_name, json.dumps(payload), evidence_doi, reason, submitter)
            )
            return cursor.lastrowid
    
    def get_proposal(self, proposal_id: int) -> Optional[Proposal]:
        """Get a proposal by ID."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM proposals WHERE id = ?",
                (proposal_id,)
            ).fetchone()
            
            if not row:
                return None
            
            return Proposal(
                id=row["id"],
                proposal_type=row["proposal_type"],
                tag_id=row["tag_id"],
                canonical_name=row["canonical_name"],
                payload=json.loads(row["payload"]),
                evidence_doi=row["evidence_doi"],
                reason=row["reason"],
                status=row["status"],
                submitter=row["submitter"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
    
    def list_proposals(
        self,
        status: Optional[str] = None,
        submitter: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Proposal]:
        """List proposals with optional filters."""
        query = "SELECT * FROM proposals WHERE 1=1"
        params = []
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        if submitter:
            query += " AND submitter = ?"
            params.append(submitter)
        
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return [
                Proposal(
                    id=row["id"],
                    proposal_type=row["proposal_type"],
                    tag_id=row["tag_id"],
                    canonical_name=row["canonical_name"],
                    payload=json.loads(row["payload"]),
                    evidence_doi=row["evidence_doi"],
                    reason=row["reason"],
                    status=row["status"],
                    submitter=row["submitter"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
                for row in rows
            ]
    
    def update_proposal_status(self, proposal_id: int, status: str) -> bool:
        """Update a proposal's status. Returns True if updated."""
        with self._connect() as conn:
            cursor = conn.execute(
                "UPDATE proposals SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, proposal_id)
            )
            return cursor.rowcount > 0
    
    def atomic_review_proposal(
        self,
        proposal_id: int,
        reviewer: str,
        decision: str,
        comment: Optional[str] = None,
    ) -> tuple[bool, str, Optional[int]]:
        """
        Atomically review a proposal with race condition protection.
        
        Returns:
            (success, message, review_id)
        """
        with self._connect() as conn:
            # Use BEGIN IMMEDIATE to get a write lock immediately
            conn.execute("BEGIN IMMEDIATE")
            try:
                # Check current status while holding lock
                row = conn.execute(
                    "SELECT status FROM proposals WHERE id = ?",
                    (proposal_id,)
                ).fetchone()
                
                if not row:
                    conn.execute("ROLLBACK")
                    return False, "Proposal not found", None
                
                current_status = row["status"]
                
                if current_status != "pending":
                    conn.execute("ROLLBACK")
                    return False, f"Proposal is already {current_status}", None
                
                # Determine new status based on decision
                if decision == "approve":
                    new_status = "approved"
                elif decision == "reject":
                    new_status = "rejected"
                else:
                    new_status = "pending"  # request_changes keeps it pending
                
                # Update proposal status
                conn.execute(
                    "UPDATE proposals SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (new_status, proposal_id)
                )
                
                # Create review record
                cursor = conn.execute(
                    """
                    INSERT INTO reviews (proposal_id, reviewer, decision, comment)
                    VALUES (?, ?, ?, ?)
                    """,
                    (proposal_id, reviewer, decision, comment)
                )
                review_id = cursor.lastrowid
                
                conn.execute("COMMIT")
                return True, f"Proposal {new_status}", review_id
                
            except Exception as e:
                conn.execute("ROLLBACK")
                raise
    
    def count_proposals(self, status: Optional[str] = None) -> int:
        """Count proposals, optionally filtered by status."""
        with self._connect() as conn:
            if status:
                row = conn.execute(
                    "SELECT COUNT(*) as count FROM proposals WHERE status = ?",
                    (status,)
                ).fetchone()
            else:
                row = conn.execute("SELECT COUNT(*) as count FROM proposals").fetchone()
            return row["count"]
    
    # ========================================================================
    # Reviews
    # ========================================================================
    
    def create_review(
        self,
        proposal_id: int,
        reviewer: str,
        decision: str,
        comment: Optional[str] = None,
    ) -> int:
        """Create a review for a proposal. Returns review ID."""
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO reviews (proposal_id, reviewer, decision, comment)
                VALUES (?, ?, ?, ?)
                """,
                (proposal_id, reviewer, decision, comment)
            )
            return cursor.lastrowid
    
    def get_reviews_for_proposal(self, proposal_id: int) -> list[Review]:
        """Get all reviews for a proposal."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM reviews WHERE proposal_id = ? ORDER BY created_at DESC",
                (proposal_id,)
            ).fetchall()
            return [
                Review(
                    id=row["id"],
                    proposal_id=row["proposal_id"],
                    reviewer=row["reviewer"],
                    decision=row["decision"],
                    comment=row["comment"],
                    created_at=row["created_at"],
                )
                for row in rows
            ]
    
    # ========================================================================
    # Releases
    # ========================================================================
    
    def record_release(
        self,
        version: str,
        registry_sha256: str,
        released_by: str,
        previous_version: Optional[str] = None,
        tags_added: int = 0,
        tags_removed: int = 0,
        tags_modified: int = 0,
        release_notes: Optional[str] = None,
    ) -> int:
        """Record a new release. Returns release ID."""
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO releases (version, previous_version, registry_sha256, 
                    tags_added, tags_removed, tags_modified, released_by, release_notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (version, previous_version, registry_sha256, 
                 tags_added, tags_removed, tags_modified, released_by, release_notes)
            )
            return cursor.lastrowid
    
    def get_latest_release(self) -> Optional[Release]:
        """Get the most recent release."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM releases ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
            
            if not row:
                return None
            
            return Release(
                id=row["id"],
                version=row["version"],
                previous_version=row["previous_version"],
                registry_sha256=row["registry_sha256"],
                tags_added=row["tags_added"],
                tags_removed=row["tags_removed"],
                tags_modified=row["tags_modified"],
                released_by=row["released_by"],
                release_notes=row["release_notes"],
                created_at=row["created_at"],
            )
    
    def list_releases(self, limit: int = 20) -> list[Release]:
        """List recent releases."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM releases ORDER BY created_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
            return [
                Release(
                    id=row["id"],
                    version=row["version"],
                    previous_version=row["previous_version"],
                    registry_sha256=row["registry_sha256"],
                    tags_added=row["tags_added"],
                    tags_removed=row["tags_removed"],
                    tags_modified=row["tags_modified"],
                    released_by=row["released_by"],
                    release_notes=row["release_notes"],
                    created_at=row["created_at"],
                )
                for row in rows
            ]
    
    # ========================================================================
    # Audit Log
    # ========================================================================
    
    def log_action(
        self,
        action: str,
        user_id: str,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        details: Optional[dict] = None,
        ip_address: Optional[str] = None,
    ) -> int:
        """Log an action to the audit log. Returns entry ID."""
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO audit_log (action, user_id, target_type, target_id, details, ip_address)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (action, user_id, target_type, target_id, 
                 json.dumps(details) if details else None, ip_address)
            )
            return cursor.lastrowid
    
    def get_audit_log(
        self,
        action: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditEntry]:
        """Get audit log entries."""
        query = "SELECT * FROM audit_log WHERE 1=1"
        params = []
        
        if action:
            query += " AND action = ?"
            params.append(action)
        
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        
        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return [
                AuditEntry(
                    id=row["id"],
                    timestamp=row["timestamp"],
                    action=row["action"],
                    user_id=row["user_id"],
                    target_type=row["target_type"],
                    target_id=row["target_id"],
                    details=json.loads(row["details"]) if row["details"] else None,
                    ip_address=row["ip_address"],
                )
                for row in rows
            ]
    
    # ========================================================================
    # API Keys
    # ========================================================================
    
    def create_api_key(
        self,
        name: str,
        role: str,
        created_by: str,
        expires_at: Optional[str] = None,
    ) -> tuple[int, str]:
        """
        Create a new API key.
        Returns (key_id, raw_key) - raw_key is only returned once!
        """
        # Generate a secure random key
        raw_key = f"trs_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        key_prefix = raw_key[:12]  # trs_xxxxxxxx
        
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO api_keys (key_hash, key_prefix, name, role, created_by, expires_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (key_hash, key_prefix, name, role, created_by, expires_at)
            )
            return cursor.lastrowid, raw_key
    
    def validate_api_key(self, raw_key: str) -> Optional[APIKey]:
        """
        Validate an API key and return its info.
        Updates last_used_at on success.
        Returns None if invalid.
        """
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM api_keys WHERE key_hash = ?",
                (key_hash,)
            ).fetchone()
            
            if not row:
                return None
            
            api_key = APIKey(
                id=row["id"],
                key_prefix=row["key_prefix"],
                name=row["name"],
                role=row["role"],
                created_by=row["created_by"],
                created_at=row["created_at"],
                last_used_at=row["last_used_at"],
                expires_at=row["expires_at"],
                revoked_at=row["revoked_at"],
            )
            
            if not api_key.is_active:
                return None
            
            # Update last used
            conn.execute(
                "UPDATE api_keys SET last_used_at = CURRENT_TIMESTAMP WHERE id = ?",
                (api_key.id,)
            )
            
            return api_key
    
    def list_api_keys(self, include_revoked: bool = False) -> list[APIKey]:
        """List all API keys."""
        query = "SELECT * FROM api_keys"
        if not include_revoked:
            query += " WHERE revoked_at IS NULL"
        query += " ORDER BY created_at DESC"
        
        with self._connect() as conn:
            rows = conn.execute(query).fetchall()
            return [
                APIKey(
                    id=row["id"],
                    key_prefix=row["key_prefix"],
                    name=row["name"],
                    role=row["role"],
                    created_by=row["created_by"],
                    created_at=row["created_at"],
                    last_used_at=row["last_used_at"],
                    expires_at=row["expires_at"],
                    revoked_at=row["revoked_at"],
                )
                for row in rows
            ]
    
    def revoke_api_key(self, key_id: int) -> bool:
        """Revoke an API key. Returns True if revoked."""
        with self._connect() as conn:
            cursor = conn.execute(
                "UPDATE api_keys SET revoked_at = CURRENT_TIMESTAMP WHERE id = ? AND revoked_at IS NULL",
                (key_id,)
            )
            return cursor.rowcount > 0
    
    # ========================================================================
    # Settings
    # ========================================================================
    
    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a setting value."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value FROM settings WHERE key = ?",
                (key,)
            ).fetchone()
            return row["value"] if row else default
    
    def set_setting(self, key: str, value: str, updated_by: Optional[str] = None) -> None:
        """Set a setting value."""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO settings (key, value, updated_by, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET 
                    value = excluded.value,
                    updated_by = excluded.updated_by,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (key, value, updated_by)
            )


# ============================================================================
# Singleton Instance
# ============================================================================

_db_instance: Optional[TRSDatabase] = None

def get_db(db_path: Optional[str | Path] = None) -> TRSDatabase:
    """Get the database singleton instance."""
    global _db_instance
    
    if _db_instance is None:
        if db_path is None:
            # Default to data/trs.db in repo root
            repo_root = Path(__file__).resolve().parents[3]
            data_dir = repo_root / "data"
            data_dir.mkdir(exist_ok=True)
            db_path = data_dir / "trs.db"
        
        _db_instance = TRSDatabase(db_path)
    
    return _db_instance


def reset_db() -> None:
    """Reset the database singleton (for testing)."""
    global _db_instance
    _db_instance = None
