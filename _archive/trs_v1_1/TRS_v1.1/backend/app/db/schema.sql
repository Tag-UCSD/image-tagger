-- TRS Database Schema
-- SQLite with WAL mode for concurrent access

-- Enable WAL mode for better concurrency
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- ============================================================================
-- Proposals: Pending tag additions/modifications
-- ============================================================================
CREATE TABLE IF NOT EXISTS proposals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    proposal_type TEXT NOT NULL CHECK (proposal_type IN ('new_tag', 'modify_tag', 'deprecate_tag')),
    tag_id TEXT NOT NULL,
    canonical_name TEXT,
    payload TEXT NOT NULL,  -- JSON blob with full tag data
    evidence_doi TEXT,
    reason TEXT,  -- Why this change is being proposed
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'merged', 'withdrawn')),
    submitter TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_proposals_status ON proposals(status);
CREATE INDEX IF NOT EXISTS idx_proposals_submitter ON proposals(submitter);
CREATE INDEX IF NOT EXISTS idx_proposals_tag_id ON proposals(tag_id);

-- ============================================================================
-- Reviews: Review decisions on proposals
-- ============================================================================
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    proposal_id INTEGER NOT NULL REFERENCES proposals(id) ON DELETE CASCADE,
    reviewer TEXT NOT NULL,
    decision TEXT NOT NULL CHECK (decision IN ('approve', 'reject', 'request_changes')),
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_reviews_proposal ON reviews(proposal_id);

-- ============================================================================
-- Releases: Release history
-- ============================================================================
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

CREATE INDEX IF NOT EXISTS idx_releases_version ON releases(version);

-- ============================================================================
-- Audit Log: All significant actions
-- ============================================================================
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    action TEXT NOT NULL,
    user_id TEXT NOT NULL,
    target_type TEXT,  -- 'proposal', 'tag', 'release', 'api_key'
    target_id TEXT,
    details TEXT,  -- JSON blob
    ip_address TEXT,
    user_agent TEXT
);

CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action);

-- ============================================================================
-- API Keys: Authentication
-- ============================================================================
CREATE TABLE IF NOT EXISTS api_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key_hash TEXT NOT NULL UNIQUE,  -- SHA256 of actual key
    key_prefix TEXT NOT NULL,  -- First 8 chars for identification (trs_xxxx)
    name TEXT NOT NULL,  -- Human-readable name
    role TEXT NOT NULL CHECK (role IN ('viewer', 'proposer', 'reviewer', 'admin')),
    created_by TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP,
    expires_at TIMESTAMP,
    revoked_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_prefix ON api_keys(key_prefix);

-- ============================================================================
-- Settings: Key-value configuration store
-- ============================================================================
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by TEXT
);

-- Insert default settings
INSERT OR IGNORE INTO settings (key, value) VALUES 
    ('require_doi', 'false'),
    ('auto_approve_threshold', '2'),
    ('release_requires_admin', 'true'),
    ('proposal_grace_period_days', '7');
