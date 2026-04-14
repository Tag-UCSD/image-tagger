#!/usr/bin/env python3
"""
TRS-106: File-based audit logging for TRS operations.

Usage:
    from scripts.audit import AuditLog
    
    audit = AuditLog()
    audit.log("release", {"version": "v0.2.9", "tags_added": 3})

Log Format:
    JSONL (one JSON object per line) in logs/audit.jsonl

Fields:
    - timestamp: ISO 8601 UTC timestamp
    - action: Action type (release, validate, propose, approve, etc.)
    - user: User identity (from git config or $USER)
    - details: Action-specific details dict
    - result: success, failure, or blocked
    - hostname: Machine hostname
"""

from __future__ import annotations
import json
import os
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


def get_user() -> str:
    """Get current user identity."""
    # Try git config first
    try:
        result = subprocess.run(
            ["git", "config", "user.email"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    
    # Fall back to environment
    return os.environ.get("USER", os.environ.get("USERNAME", "unknown"))


class AuditLog:
    """File-based audit logger."""
    
    def __init__(self, log_dir: Optional[Path] = None):
        if log_dir is None:
            # Default to logs/ in repo root
            script_dir = Path(__file__).resolve().parent
            repo_root = script_dir.parent
            log_dir = repo_root / "logs"
        
        self.log_dir = Path(log_dir)
        self.log_file = self.log_dir / "audit.jsonl"
        self._ensure_log_dir()
    
    def _ensure_log_dir(self) -> None:
        """Create log directory if needed."""
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create .gitignore to prevent committing logs
        gitignore = self.log_dir / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text("# Ignore audit logs\n*.jsonl\n")
    
    def log(
        self,
        action: str,
        details: Optional[dict[str, Any]] = None,
        result: str = "success",
        user: Optional[str] = None,
    ) -> dict:
        """
        Log an action to the audit file.
        
        Args:
            action: Action type (release, validate, propose, etc.)
            details: Action-specific details
            result: success, failure, or blocked
            user: User identity (auto-detected if not provided)
        
        Returns:
            The logged entry dict
        """
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "user": user or get_user(),
            "hostname": socket.gethostname(),
            "result": result,
            "details": details or {},
        }
        
        # Append to log file
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        
        return entry
    
    def log_release(
        self,
        version: str,
        previous_version: Optional[str],
        tags_added: int = 0,
        tags_removed: int = 0,
        tags_modified: int = 0,
        registry_sha256: Optional[str] = None,
        result: str = "success",
    ) -> dict:
        """Log a release action."""
        return self.log(
            action="release",
            details={
                "version": version,
                "previous_version": previous_version,
                "tags_added": tags_added,
                "tags_removed": tags_removed,
                "tags_modified": tags_modified,
                "registry_sha256": registry_sha256,
            },
            result=result,
        )
    
    def log_validation(
        self,
        registry_path: str,
        errors: int,
        warnings: int,
        result: str = "success",
    ) -> dict:
        """Log a validation action."""
        return self.log(
            action="validation",
            details={
                "registry_path": registry_path,
                "errors": errors,
                "warnings": warnings,
            },
            result=result,
        )
    
    def log_diff(
        self,
        old_version: str,
        new_version: str,
        breaking: int,
        warnings: int,
        info: int,
        result: str = "success",
    ) -> dict:
        """Log a diff check action."""
        return self.log(
            action="diff_check",
            details={
                "old_version": old_version,
                "new_version": new_version,
                "breaking_changes": breaking,
                "warnings": warnings,
                "info_changes": info,
            },
            result=result,
        )
    
    def get_recent(self, limit: int = 50) -> list[dict]:
        """Get recent log entries."""
        if not self.log_file.exists():
            return []
        
        entries = []
        with open(self.log_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        
        return entries[-limit:]


# Convenience function for scripts
_default_audit: Optional[AuditLog] = None

def get_audit_log() -> AuditLog:
    """Get the default audit log instance."""
    global _default_audit
    if _default_audit is None:
        _default_audit = AuditLog()
    return _default_audit


if __name__ == "__main__":
    # Test the audit log
    audit = AuditLog()
    
    print("Testing audit log...")
    entry = audit.log("test", {"message": "This is a test"})
    print(f"Logged: {entry}")
    
    print(f"\nLog file: {audit.log_file}")
    print(f"Recent entries: {len(audit.get_recent())}")
