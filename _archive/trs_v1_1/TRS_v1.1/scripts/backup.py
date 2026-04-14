#!/usr/bin/env python3
"""
TRS-405: Database backup and restore utility.

Usage:
    # Backup
    python scripts/backup.py backup
    python scripts/backup.py backup --output /path/to/backup.db
    
    # Restore
    python scripts/backup.py restore backup_20241221_120000.db
    
    # List backups
    python scripts/backup.py list

Backups are stored in data/backups/ with timestamps.
"""

from __future__ import annotations
import argparse
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# Add parent to path
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent

DATA_DIR = REPO_ROOT / "data"
BACKUP_DIR = DATA_DIR / "backups"
DB_PATH = DATA_DIR / "trs.db"


def ensure_dirs():
    """Create necessary directories."""
    DATA_DIR.mkdir(exist_ok=True)
    BACKUP_DIR.mkdir(exist_ok=True)


def get_db_stats(db_path: Path) -> dict:
    """Get statistics from a database."""
    if not db_path.exists():
        return {"exists": False}
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        stats = {"exists": True, "size_bytes": db_path.stat().st_size}
        
        # Count tables
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        stats["tables"] = [t["name"] for t in tables]
        
        # Count rows in key tables
        for table in ["proposals", "reviews", "releases", "api_keys", "audit_log"]:
            try:
                count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                stats[f"{table}_count"] = count
            except sqlite3.OperationalError:
                pass
        
        conn.close()
        return stats
    except Exception as e:
        return {"exists": True, "error": str(e)}


def cmd_backup(args):
    """Create a database backup."""
    ensure_dirs()
    
    if not DB_PATH.exists():
        print(f"Database not found: {DB_PATH}")
        return 1
    
    # Determine output path
    if args.output:
        backup_path = Path(args.output)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = BACKUP_DIR / f"trs_backup_{timestamp}.db"
    
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create backup using SQLite's backup API for consistency
    print(f"Backing up {DB_PATH}...")
    
    source = sqlite3.connect(DB_PATH)
    dest = sqlite3.connect(backup_path)
    
    source.backup(dest)
    
    source.close()
    dest.close()
    
    # Get stats
    stats = get_db_stats(backup_path)
    
    print(f"Backup created: {backup_path}")
    print(f"  Size: {stats.get('size_bytes', 0):,} bytes")
    print(f"  Proposals: {stats.get('proposals_count', 0)}")
    print(f"  Reviews: {stats.get('reviews_count', 0)}")
    print(f"  Releases: {stats.get('releases_count', 0)}")
    print(f"  API Keys: {stats.get('api_keys_count', 0)}")
    print(f"  Audit Entries: {stats.get('audit_log_count', 0)}")
    
    return 0


def cmd_restore(args):
    """Restore a database backup."""
    backup_path = Path(args.backup)
    
    if not backup_path.exists():
        # Try looking in backup directory
        backup_path = BACKUP_DIR / args.backup
    
    if not backup_path.exists():
        print(f"Backup not found: {args.backup}")
        return 1
    
    # Verify it's a valid SQLite database
    try:
        conn = sqlite3.connect(backup_path)
        conn.execute("SELECT 1")
        conn.close()
    except Exception as e:
        print(f"Invalid database file: {e}")
        return 1
    
    # Backup current database first (if exists)
    if DB_PATH.exists() and not args.force:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pre_restore_backup = BACKUP_DIR / f"trs_pre_restore_{timestamp}.db"
        ensure_dirs()
        shutil.copy2(DB_PATH, pre_restore_backup)
        print(f"Current database backed up to: {pre_restore_backup}")
    
    # Restore
    print(f"Restoring from: {backup_path}")
    
    source = sqlite3.connect(backup_path)
    dest = sqlite3.connect(DB_PATH)
    
    # Clear destination first
    dest.executescript("PRAGMA writable_schema = 1; DELETE FROM sqlite_master; PRAGMA writable_schema = 0; VACUUM;")
    
    source.backup(dest)
    
    source.close()
    dest.close()
    
    # Get stats
    stats = get_db_stats(DB_PATH)
    
    print(f"Restore complete!")
    print(f"  Proposals: {stats.get('proposals_count', 0)}")
    print(f"  Reviews: {stats.get('reviews_count', 0)}")
    print(f"  Releases: {stats.get('releases_count', 0)}")
    
    return 0


def cmd_list(args):
    """List available backups."""
    ensure_dirs()
    
    backups = sorted(BACKUP_DIR.glob("*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
    
    if not backups:
        print("No backups found.")
        return 0
    
    print()
    print(f"{'Filename':<45} {'Size':<12} {'Modified':<20}")
    print("-" * 80)
    
    for backup in backups:
        size = f"{backup.stat().st_size:,}"
        mtime = datetime.fromtimestamp(backup.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        print(f"{backup.name:<45} {size:<12} {mtime:<20}")
    
    print()
    print(f"Total: {len(backups)} backups in {BACKUP_DIR}")
    return 0


def cmd_verify(args):
    """Verify a backup is valid."""
    backup_path = Path(args.backup)
    
    if not backup_path.exists():
        backup_path = BACKUP_DIR / args.backup
    
    if not backup_path.exists():
        print(f"Backup not found: {args.backup}")
        return 1
    
    print(f"Verifying: {backup_path}")
    
    stats = get_db_stats(backup_path)
    
    if not stats.get("exists"):
        print("  ❌ File does not exist")
        return 1
    
    if stats.get("error"):
        print(f"  ❌ Error: {stats['error']}")
        return 1
    
    print(f"  ✓ Valid SQLite database")
    print(f"  Size: {stats.get('size_bytes', 0):,} bytes")
    print(f"  Tables: {', '.join(stats.get('tables', []))}")
    print(f"  Proposals: {stats.get('proposals_count', 0)}")
    print(f"  Reviews: {stats.get('reviews_count', 0)}")
    
    return 0


def main():
    parser = argparse.ArgumentParser(description="TRS Database Backup Utility")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # backup
    p_backup = subparsers.add_parser("backup", help="Create a backup")
    p_backup.add_argument("--output", "-o", help="Output path")
    p_backup.set_defaults(func=cmd_backup)
    
    # restore
    p_restore = subparsers.add_parser("restore", help="Restore from backup")
    p_restore.add_argument("backup", help="Backup file to restore")
    p_restore.add_argument("--force", "-f", action="store_true", help="Skip pre-restore backup")
    p_restore.set_defaults(func=cmd_restore)
    
    # list
    p_list = subparsers.add_parser("list", help="List available backups")
    p_list.set_defaults(func=cmd_list)
    
    # verify
    p_verify = subparsers.add_parser("verify", help="Verify a backup")
    p_verify.add_argument("backup", help="Backup file to verify")
    p_verify.set_defaults(func=cmd_verify)
    
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
