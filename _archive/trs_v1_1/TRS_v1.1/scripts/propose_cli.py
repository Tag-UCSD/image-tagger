#!/usr/bin/env python3
"""
TRS-303: CLI for submitting and managing proposals.

Usage:
    python scripts/propose_cli.py new env.test.tag "Test Tag" --value-type ordinal
    python scripts/propose_cli.py modify env.existing.tag --payload '{"definition": "Updated"}'
    python scripts/propose_cli.py deprecate env.old.tag --replaced-by env.new.tag
    python scripts/propose_cli.py list
    python scripts/propose_cli.py list --status pending
    python scripts/propose_cli.py show 1
    python scripts/propose_cli.py approve 1 --comment "Looks good"
    python scripts/propose_cli.py reject 1 --comment "Needs work"
"""

from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

# Add parent to path
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(REPO_ROOT))

from backend.app.db import get_db


def cmd_new(args):
    """Create a new tag proposal."""
    db = get_db()
    
    # Build payload
    payload = {
        "canonical_name": args.canonical_name,
        "value_type": args.value_type,
        "status": "proposed",
        "definition": args.definition or "",
    }
    
    if args.domain:
        payload["domain"] = args.domain
    
    if args.aliases:
        payload["semantics"] = {"aliases": [a.strip() for a in args.aliases.split(",")]}
    
    # Merge extra payload if provided
    if args.payload:
        extra = json.loads(args.payload)
        payload.update(extra)
    
    proposal_id = db.create_proposal(
        proposal_type="new_tag",
        tag_id=args.tag_id,
        canonical_name=args.canonical_name,
        payload=payload,
        submitter=args.submitter,
        evidence_doi=args.doi,
        reason=args.reason,
    )
    
    db.log_action(
        action="proposal_created",
        user_id=args.submitter,
        target_type="proposal",
        target_id=str(proposal_id),
        details={"tag_id": args.tag_id, "type": "new_tag"},
    )
    
    print(f"Created proposal #{proposal_id}")
    print(f"  Tag ID: {args.tag_id}")
    print(f"  Name: {args.canonical_name}")
    print(f"  Status: pending")
    return 0


def cmd_modify(args):
    """Create a modify tag proposal."""
    db = get_db()
    
    # Parse payload
    if not args.payload:
        print("ERROR: --payload required for modify proposals")
        return 1
    
    payload = json.loads(args.payload)
    
    proposal_id = db.create_proposal(
        proposal_type="modify_tag",
        tag_id=args.tag_id,
        payload=payload,
        submitter=args.submitter,
        evidence_doi=args.doi,
        reason=args.reason,
    )
    
    db.log_action(
        action="proposal_created",
        user_id=args.submitter,
        target_type="proposal",
        target_id=str(proposal_id),
        details={"tag_id": args.tag_id, "type": "modify_tag"},
    )
    
    print(f"Created proposal #{proposal_id}")
    print(f"  Tag ID: {args.tag_id}")
    print(f"  Type: modify_tag")
    return 0


def cmd_deprecate(args):
    """Create a deprecate tag proposal."""
    db = get_db()
    
    payload = {}
    if args.replaced_by:
        payload["replaced_by"] = args.replaced_by
    
    proposal_id = db.create_proposal(
        proposal_type="deprecate_tag",
        tag_id=args.tag_id,
        payload=payload,
        submitter=args.submitter,
        evidence_doi=args.doi,
        reason=args.reason or f"Deprecating in favor of {args.replaced_by}" if args.replaced_by else None,
    )
    
    db.log_action(
        action="proposal_created",
        user_id=args.submitter,
        target_type="proposal",
        target_id=str(proposal_id),
        details={"tag_id": args.tag_id, "type": "deprecate_tag"},
    )
    
    print(f"Created proposal #{proposal_id}")
    print(f"  Tag ID: {args.tag_id}")
    print(f"  Type: deprecate_tag")
    if args.replaced_by:
        print(f"  Replaced by: {args.replaced_by}")
    return 0


def cmd_list(args):
    """List proposals."""
    db = get_db()
    
    proposals = db.list_proposals(status=args.status, limit=args.limit)
    
    if not proposals:
        print("No proposals found.")
        return 0
    
    print()
    print(f"{'ID':<4} {'Status':<10} {'Type':<12} {'Tag ID':<50} {'Submitter':<20}")
    print("-" * 100)
    
    for p in proposals:
        tag_id = p.tag_id[:48] + ".." if len(p.tag_id) > 50 else p.tag_id
        submitter = p.submitter[:18] + ".." if len(p.submitter) > 20 else p.submitter
        print(f"{p.id:<4} {p.status:<10} {p.proposal_type:<12} {tag_id:<50} {submitter:<20}")
    
    print()
    print(f"Total: {len(proposals)} proposals")
    return 0


def cmd_show(args):
    """Show proposal details."""
    db = get_db()
    
    proposal = db.get_proposal(args.proposal_id)
    
    if not proposal:
        print(f"Proposal #{args.proposal_id} not found.")
        return 1
    
    print()
    print(f"Proposal #{proposal.id}")
    print("=" * 50)
    print(f"  Type:      {proposal.proposal_type}")
    print(f"  Tag ID:    {proposal.tag_id}")
    print(f"  Name:      {proposal.canonical_name or 'N/A'}")
    print(f"  Status:    {proposal.status}")
    print(f"  Submitter: {proposal.submitter}")
    print(f"  Created:   {proposal.created_at}")
    
    if proposal.evidence_doi:
        print(f"  DOI:       {proposal.evidence_doi}")
    
    if proposal.reason:
        print(f"  Reason:    {proposal.reason}")
    
    print()
    print("Payload:")
    print(json.dumps(proposal.payload, indent=2))
    
    # Show reviews
    reviews = db.get_reviews_for_proposal(args.proposal_id)
    if reviews:
        print()
        print("Reviews:")
        for r in reviews:
            print(f"  [{r.decision}] by {r.reviewer} at {r.created_at}")
            if r.comment:
                print(f"    Comment: {r.comment}")
    
    return 0


def cmd_approve(args):
    """Approve a proposal."""
    db = get_db()
    
    proposal = db.get_proposal(args.proposal_id)
    if not proposal:
        print(f"Proposal #{args.proposal_id} not found.")
        return 1
    
    if proposal.status != "pending":
        print(f"Cannot approve proposal with status '{proposal.status}'.")
        return 1
    
    review_id = db.create_review(
        proposal_id=args.proposal_id,
        reviewer=args.reviewer,
        decision="approve",
        comment=args.comment,
    )
    
    db.update_proposal_status(args.proposal_id, "approved")
    
    db.log_action(
        action="proposal_reviewed",
        user_id=args.reviewer,
        target_type="proposal",
        target_id=str(args.proposal_id),
        details={"decision": "approve"},
    )
    
    print(f"Proposal #{args.proposal_id} approved.")
    return 0


def cmd_reject(args):
    """Reject a proposal."""
    db = get_db()
    
    proposal = db.get_proposal(args.proposal_id)
    if not proposal:
        print(f"Proposal #{args.proposal_id} not found.")
        return 1
    
    if proposal.status != "pending":
        print(f"Cannot reject proposal with status '{proposal.status}'.")
        return 1
    
    if not args.comment:
        print("ERROR: --comment required for rejections")
        return 1
    
    review_id = db.create_review(
        proposal_id=args.proposal_id,
        reviewer=args.reviewer,
        decision="reject",
        comment=args.comment,
    )
    
    db.update_proposal_status(args.proposal_id, "rejected")
    
    db.log_action(
        action="proposal_reviewed",
        user_id=args.reviewer,
        target_type="proposal",
        target_id=str(args.proposal_id),
        details={"decision": "reject"},
    )
    
    print(f"Proposal #{args.proposal_id} rejected.")
    return 0


def main():
    parser = argparse.ArgumentParser(description="TRS Proposal Management CLI")
    parser.add_argument("--submitter", default="cli@localhost", help="Submitter identity")
    parser.add_argument("--reviewer", default="cli@localhost", help="Reviewer identity")
    
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # new
    p_new = subparsers.add_parser("new", help="Create new tag proposal")
    p_new.add_argument("tag_id", help="Tag ID (e.g., env.lighting.warmth)")
    p_new.add_argument("canonical_name", help="Canonical name")
    p_new.add_argument("--value-type", default="ordinal", choices=["ordinal", "binary", "continuous", "categorical"])
    p_new.add_argument("--domain", help="Domain name")
    p_new.add_argument("--definition", help="Tag definition")
    p_new.add_argument("--aliases", help="Comma-separated aliases")
    p_new.add_argument("--doi", help="Evidence DOI")
    p_new.add_argument("--reason", help="Reason for proposal")
    p_new.add_argument("--payload", help="Extra JSON payload")
    p_new.set_defaults(func=cmd_new)
    
    # modify
    p_modify = subparsers.add_parser("modify", help="Modify existing tag")
    p_modify.add_argument("tag_id", help="Tag ID to modify")
    p_modify.add_argument("--payload", required=True, help="JSON payload with updates")
    p_modify.add_argument("--doi", help="Evidence DOI")
    p_modify.add_argument("--reason", help="Reason for modification")
    p_modify.set_defaults(func=cmd_modify)
    
    # deprecate
    p_deprecate = subparsers.add_parser("deprecate", help="Deprecate a tag")
    p_deprecate.add_argument("tag_id", help="Tag ID to deprecate")
    p_deprecate.add_argument("--replaced-by", help="Replacement tag ID")
    p_deprecate.add_argument("--doi", help="Evidence DOI")
    p_deprecate.add_argument("--reason", help="Reason for deprecation")
    p_deprecate.set_defaults(func=cmd_deprecate)
    
    # list
    p_list = subparsers.add_parser("list", help="List proposals")
    p_list.add_argument("--status", choices=["pending", "approved", "rejected", "merged", "withdrawn"])
    p_list.add_argument("--limit", type=int, default=50)
    p_list.set_defaults(func=cmd_list)
    
    # show
    p_show = subparsers.add_parser("show", help="Show proposal details")
    p_show.add_argument("proposal_id", type=int, help="Proposal ID")
    p_show.set_defaults(func=cmd_show)
    
    # approve
    p_approve = subparsers.add_parser("approve", help="Approve a proposal")
    p_approve.add_argument("proposal_id", type=int, help="Proposal ID")
    p_approve.add_argument("--comment", help="Review comment")
    p_approve.set_defaults(func=cmd_approve)
    
    # reject
    p_reject = subparsers.add_parser("reject", help="Reject a proposal")
    p_reject.add_argument("proposal_id", type=int, help="Proposal ID")
    p_reject.add_argument("--comment", required=True, help="Rejection reason")
    p_reject.set_defaults(func=cmd_reject)
    
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
