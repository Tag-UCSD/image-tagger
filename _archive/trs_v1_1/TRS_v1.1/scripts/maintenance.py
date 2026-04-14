#!/usr/bin/env python3
"""
TRS-704 & TRS-705: Maintenance tasks.

Provides:
- Audit log retention and cleanup
- API key rotation
- Database maintenance

Usage:
    python scripts/maintenance.py cleanup-audit --days 90
    python scripts/maintenance.py rotate-key 1 --reason "Scheduled rotation"
    python scripts/maintenance.py vacuum
"""

from __future__ import annotations
import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add parent to path
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(REPO_ROOT))

from backend.app.db import get_db


def cmd_cleanup_audit(args):
    """Clean up old audit log entries."""
    db = get_db()
    
    cutoff_date = datetime.now() - timedelta(days=args.days)
    cutoff_str = cutoff_date.isoformat()
    
    print(f"Cleaning audit entries older than {args.days} days...")
    print(f"Cutoff date: {cutoff_str}")
    
    if args.dry_run:
        # Count entries that would be deleted
        with db._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM audit_log WHERE timestamp < ?",
                (cutoff_str,)
            ).fetchone()
            count = row[0]
        
        print(f"Would delete {count} entries (dry run)")
        return 0
    
    # Delete old entries
    with db._connect() as conn:
        cursor = conn.execute(
            "DELETE FROM audit_log WHERE timestamp < ?",
            (cutoff_str,)
        )
        deleted = cursor.rowcount
    
    print(f"Deleted {deleted} audit log entries")
    
    # Log the cleanup
    db.log_action(
        action="audit_cleanup",
        user_id="maintenance",
        details={"deleted": deleted, "cutoff_days": args.days},
    )
    
    return 0


def cmd_rotate_key(args):
    """Rotate an API key."""
    db = get_db()
    
    # Get existing key info
    with db._connect() as conn:
        row = conn.execute(
            "SELECT * FROM api_keys WHERE id = ?",
            (args.key_id,)
        ).fetchone()
    
    if not row:
        print(f"API key {args.key_id} not found")
        return 1
    
    old_name = row["name"]
    old_role = row["role"]
    
    print(f"Rotating API key {args.key_id}: {old_name} ({old_role})")
    
    if args.dry_run:
        print("Would revoke old key and create new one (dry run)")
        return 0
    
    # Revoke old key
    db.revoke_api_key(args.key_id)
    
    # Create new key with same name/role
    new_name = f"{old_name} (rotated {datetime.now().strftime('%Y%m%d')})"
    new_id, new_key = db.create_api_key(
        name=new_name,
        role=old_role,
        created_by="maintenance",
    )
    
    # Log the rotation
    db.log_action(
        action="api_key_rotated",
        user_id="maintenance",
        target_type="api_key",
        target_id=str(args.key_id),
        details={
            "old_key_id": args.key_id,
            "new_key_id": new_id,
            "reason": args.reason,
        },
    )
    
    print()
    print("=" * 60)
    print(f"Old key {args.key_id} revoked")
    print(f"New key created: {new_id}")
    print()
    print(f"NEW KEY: {new_key}")
    print()
    print("⚠️  SAVE THIS KEY NOW - it cannot be retrieved later!")
    print("=" * 60)
    
    return 0


def cmd_expire_keys(args):
    """Check and expire old API keys."""
    db = get_db()
    
    # Find keys that haven't been used in X days
    cutoff = datetime.now() - timedelta(days=args.days)
    cutoff_str = cutoff.isoformat()
    
    with db._connect() as conn:
        rows = conn.execute(
            """
            SELECT id, name, role, last_used_at, created_at
            FROM api_keys
            WHERE revoked_at IS NULL
            AND (last_used_at IS NULL OR last_used_at < ?)
            AND created_at < ?
            """,
            (cutoff_str, cutoff_str)
        ).fetchall()
    
    if not rows:
        print(f"No keys inactive for {args.days}+ days")
        return 0
    
    print(f"Found {len(rows)} inactive keys:")
    for row in rows:
        last_used = row["last_used_at"] or "Never"
        print(f"  {row['id']}: {row['name']} (role={row['role']}, last={last_used})")
    
    if args.dry_run:
        print("\nWould revoke these keys (dry run)")
        return 0
    
    if not args.force:
        confirm = input("\nRevoke these keys? [y/N] ")
        if confirm.lower() != "y":
            print("Cancelled")
            return 0
    
    # Revoke keys
    for row in rows:
        db.revoke_api_key(row["id"])
        db.log_action(
            action="api_key_expired",
            user_id="maintenance",
            target_type="api_key",
            target_id=str(row["id"]),
            details={"reason": f"Inactive for {args.days}+ days"},
        )
    
    print(f"\nRevoked {len(rows)} keys")
    return 0


def cmd_vacuum(args):
    """Vacuum the database to reclaim space."""
    db = get_db()
    
    # Get size before
    db_path = db.db_path
    size_before = db_path.stat().st_size
    
    print(f"Database: {db_path}")
    print(f"Size before: {size_before:,} bytes")
    
    if args.dry_run:
        print("Would vacuum database (dry run)")
        return 0
    
    # Vacuum
    with db._connect() as conn:
        conn.execute("VACUUM")
    
    size_after = db_path.stat().st_size
    saved = size_before - size_after
    
    print(f"Size after: {size_after:,} bytes")
    print(f"Space saved: {saved:,} bytes ({saved/size_before*100:.1f}%)")
    
    return 0


def cmd_stats(args):
    """Show database statistics."""
    db = get_db()
    
    print("Database Statistics")
    print("=" * 50)
    
    with db._connect() as conn:
        # Table sizes
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        
        print("\nTable Row Counts:")
        for table in tables:
            name = table["name"]
            count = conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
            print(f"  {name}: {count:,}")
        
        # Proposal stats
        print("\nProposal Status:")
        for status in ["pending", "approved", "rejected", "merged"]:
            count = db.count_proposals(status)
            print(f"  {status}: {count}")
        
        # API key stats
        keys = db.list_api_keys(include_revoked=True)
        active = sum(1 for k in keys if k.is_active)
        print(f"\nAPI Keys: {active} active / {len(keys)} total")
        
        # Database size
        db_path = db.db_path
        size = db_path.stat().st_size
        print(f"\nDatabase size: {size:,} bytes")
    
    return 0


def main():
    parser = argparse.ArgumentParser(description="TRS Maintenance Tasks")
    parser.add_argument("--dry-run", action="store_true", help="Don't make changes")
    
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # cleanup-audit
    p_audit = subparsers.add_parser("cleanup-audit", help="Clean old audit entries")
    p_audit.add_argument("--days", type=int, default=90, help="Keep entries newer than X days")
    p_audit.set_defaults(func=cmd_cleanup_audit)
    
    # rotate-key
    p_rotate = subparsers.add_parser("rotate-key", help="Rotate an API key")
    p_rotate.add_argument("key_id", type=int, help="Key ID to rotate")
    p_rotate.add_argument("--reason", default="Manual rotation", help="Reason for rotation")
    p_rotate.set_defaults(func=cmd_rotate_key)
    
    # expire-keys
    p_expire = subparsers.add_parser("expire-keys", help="Expire inactive keys")
    p_expire.add_argument("--days", type=int, default=90, help="Expire if inactive for X days")
    p_expire.add_argument("--force", action="store_true", help="Don't prompt for confirmation")
    p_expire.set_defaults(func=cmd_expire_keys)
    
    # vacuum
    p_vacuum = subparsers.add_parser("vacuum", help="Vacuum database")
    p_vacuum.set_defaults(func=cmd_vacuum)
    
    # stats
    p_stats = subparsers.add_parser("stats", help="Show database statistics")
    p_stats.set_defaults(func=cmd_stats)
    
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
