#!/usr/bin/env python3
"""
TRS Key Management CLI

Usage:
    python bin/keys.py create "Student RA" proposer
    python bin/keys.py list
    python bin/keys.py revoke 1
"""

import argparse
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.auth import create_key_cli, list_keys_cli, revoke_key_cli, ROLE_HIERARCHY


def cmd_create(args):
    """Create a new API key."""
    try:
        key_id, raw_key = create_key_cli(args.name, args.role, args.created_by or "cli")
        print()
        print("=" * 60)
        print(f"API Key Created Successfully!")
        print("=" * 60)
        print()
        print(f"  ID:   {key_id}")
        print(f"  Name: {args.name}")
        print(f"  Role: {args.role}")
        print()
        print(f"  Key:  {raw_key}")
        print()
        print("⚠️  SAVE THIS KEY NOW - it cannot be retrieved later!")
        print()
    except Exception as e:
        print(f"Error: {e}")
        return 1
    return 0


def cmd_list(args):
    """List all API keys."""
    keys = list_keys_cli()
    
    if not keys:
        print("No API keys found.")
        return 0
    
    print()
    print(f"{'ID':<4} {'Name':<25} {'Role':<12} {'Prefix':<14} {'Created':<20} {'Last Used':<20}")
    print("-" * 100)
    
    for k in keys:
        last_used = k.last_used_at[:19] if k.last_used_at else "Never"
        created = k.created_at[:19] if k.created_at else "?"
        print(f"{k.id:<4} {k.name:<25} {k.role:<12} {k.key_prefix:<14} {created:<20} {last_used:<20}")
    
    print()
    return 0


def cmd_revoke(args):
    """Revoke an API key."""
    success = revoke_key_cli(args.key_id, args.revoked_by or "cli")
    
    if success:
        print(f"Key {args.key_id} revoked successfully.")
        return 0
    else:
        print(f"Key {args.key_id} not found or already revoked.")
        return 1


def main():
    parser = argparse.ArgumentParser(description="TRS API Key Management")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # create
    p_create = subparsers.add_parser("create", help="Create a new API key")
    p_create.add_argument("name", help="Human-readable name for the key")
    p_create.add_argument("role", choices=list(ROLE_HIERARCHY.keys()), help="Role for the key")
    p_create.add_argument("--created-by", help="Who is creating this key")
    p_create.set_defaults(func=cmd_create)
    
    # list
    p_list = subparsers.add_parser("list", help="List all API keys")
    p_list.set_defaults(func=cmd_list)
    
    # revoke
    p_revoke = subparsers.add_parser("revoke", help="Revoke an API key")
    p_revoke.add_argument("key_id", type=int, help="Key ID to revoke")
    p_revoke.add_argument("--revoked-by", help="Who is revoking this key")
    p_revoke.set_defaults(func=cmd_revoke)
    
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
