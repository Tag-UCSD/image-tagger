"""Mint HS256 bearer JWTs for image-tagger roles (local smoke / demo).

Tokens are signed with ``SUPABASE_JWT_SECRET`` and include top-level claims
``sub`` and ``role`` as required by ``backend/services/auth.py``.

Usage (from repo root)::

    # Ensure SUPABASE_JWT_SECRET is set (e.g. in .env)
    python -m backend.scripts.mint_role_jwts

    # Longer-lived tokens (default 24h)
    python -m backend.scripts.mint_role_jwts --hours 168

    # Shell exports only (no banner)
    python -m backend.scripts.mint_role_jwts --export-only

The secret must match the Supabase project JWT secret (and Render
``SUPABASE_JWT_SECRET``) or protected API routes will return 401.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import uuid

from jose import jwt

from backend.services.auth import ALLOWED_ROLES, JWT_ALGORITHM

try:
    from dotenv import load_dotenv

    load_dotenv(override=False)
except Exception:
    pass


def mint_jwt(
    role: str,
    *,
    secret: str,
    sub: str | None = None,
    hours: float = 24.0,
) -> str:
    now = int(time.time())
    ttl = max(1, int(hours * 3600))
    return jwt.encode(
        {
            "sub": sub or f"demo-{role}-{uuid.uuid4().hex[:8]}",
            "role": role,
            "aud": "authenticated",
            "iat": now,
            "exp": now + ttl,
        },
        secret,
        algorithm=JWT_ALGORITHM,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Mint role JWTs for image-tagger.")
    parser.add_argument(
        "--hours",
        type=float,
        default=24.0,
        help="Token lifetime in hours (default: 24).",
    )
    parser.add_argument(
        "--roles",
        nargs="*",
        default=list(ALLOWED_ROLES),
        choices=ALLOWED_ROLES,
        metavar="ROLE",
        help=f"Roles to mint (default: all {ALLOWED_ROLES}).",
    )
    parser.add_argument(
        "--export-only",
        action="store_true",
        help="Print only export lines (no comments).",
    )
    args = parser.parse_args()

    secret = (os.environ.get("SUPABASE_JWT_SECRET") or "").strip()
    if not secret:
        print(
            "error: SUPABASE_JWT_SECRET is not set.\n"
            "  Copy from Supabase → Project Settings → API → JWT Secret\n"
            "  into .env (see .env.example) and re-run.",
            file=sys.stderr,
        )
        return 1

    tokens = {
        role: mint_jwt(role, secret=secret, hours=args.hours) for role in args.roles
    }

    smoke_map = {
        "admin": "SMOKE_ADMIN_JWT",
        "tagger": "SMOKE_TAGGER_JWT",
        "supervisor": "SMOKE_SUPERVISOR_JWT",
    }
    demo_map = {
        "admin": "VITE_DEMO_ADMIN_JWT",
        "tagger": "VITE_DEMO_TAGGER_JWT",
        "supervisor": "VITE_DEMO_SUPERVISOR_JWT",
    }

    if not args.export_only:
        print(f"# Minted {len(tokens)} token(s); expires in ~{args.hours}h")
        print("# Uses SUPABASE_JWT_SECRET from environment\n")

    for role, token in tokens.items():
        if args.export_only:
            if role in smoke_map:
                print(f'export {smoke_map[role]}="{token}"')
            continue

        print(f"## {role}")
        print(token)
        print()
        if role in smoke_map:
            print(f'export {smoke_map[role]}="{token}"')
        if role in demo_map:
            print(f"# frontend .env.local: {demo_map[role]}={token}")
        print()

    if not args.export_only and "scientist" in tokens:
        print("# scientist: no SMOKE_* / VITE_DEMO_* alias in repo; use Bearer header directly")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
