"""
TRS-204 + TRS-205: Proposal and Release API endpoints.

Provides REST API for:
- Creating and managing tag proposals
- Reviewing proposals
- Triggering releases

All write endpoints require authentication.
"""

from __future__ import annotations
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from .auth import require_auth, require_role, optional_auth
from .db import get_db, APIKey, Proposal


# ============================================================================
# Request/Response Models
# ============================================================================

class ProposalCreate(BaseModel):
    """Request model for creating a proposal."""
    proposal_type: str = Field(..., pattern="^(new_tag|modify_tag|deprecate_tag)$")
    tag_id: str = Field(..., min_length=3, max_length=200)
    canonical_name: Optional[str] = Field(None, max_length=200)
    payload: dict = Field(..., description="Full tag data as JSON")
    evidence_doi: Optional[str] = Field(None, max_length=200)
    reason: Optional[str] = Field(None, max_length=1000)


class ProposalResponse(BaseModel):
    """Response model for a proposal."""
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


class ReviewCreate(BaseModel):
    """Request model for creating a review."""
    decision: str = Field(..., pattern="^(approve|reject|request_changes)$")
    comment: Optional[str] = Field(None, max_length=2000)


class ReviewResponse(BaseModel):
    """Response model for a review."""
    id: int
    proposal_id: int
    reviewer: str
    decision: str
    comment: Optional[str]
    created_at: str


class ReleaseCreate(BaseModel):
    """Request model for creating a release."""
    version: str = Field(..., pattern="^v[0-9]+\\.[0-9]+\\.[0-9]+$")
    release_notes: Optional[str] = Field(None, max_length=5000)


class ReleaseResponse(BaseModel):
    """Response model for a release."""
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


# ============================================================================
# Router
# ============================================================================

router = APIRouter(tags=["proposals"])


# ============================================================================
# Proposal Endpoints
# ============================================================================

@router.get("/proposals", response_model=list[ProposalResponse])
async def list_proposals(
    status: Optional[str] = Query(None, pattern="^(pending|approved|rejected|merged|withdrawn)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: Optional[APIKey] = Depends(optional_auth),
):
    """
    List proposals with optional status filter.
    Public read access (no auth required).
    """
    db = get_db()
    proposals = db.list_proposals(status=status, limit=limit, offset=offset)
    
    return [
        ProposalResponse(
            id=p.id,
            proposal_type=p.proposal_type,
            tag_id=p.tag_id,
            canonical_name=p.canonical_name,
            payload=p.payload,
            evidence_doi=p.evidence_doi,
            reason=p.reason,
            status=p.status,
            submitter=p.submitter,
            created_at=p.created_at,
            updated_at=p.updated_at,
        )
        for p in proposals
    ]


@router.get("/proposals/stats")
async def proposal_stats():
    """Get proposal statistics."""
    db = get_db()
    return {
        "total": db.count_proposals(),
        "pending": db.count_proposals("pending"),
        "approved": db.count_proposals("approved"),
        "rejected": db.count_proposals("rejected"),
        "merged": db.count_proposals("merged"),
    }


@router.get("/proposals/{proposal_id}", response_model=ProposalResponse)
async def get_proposal(
    proposal_id: int,
    user: Optional[APIKey] = Depends(optional_auth),
):
    """Get a proposal by ID."""
    db = get_db()
    proposal = db.get_proposal(proposal_id)
    
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    return ProposalResponse(
        id=proposal.id,
        proposal_type=proposal.proposal_type,
        tag_id=proposal.tag_id,
        canonical_name=proposal.canonical_name,
        payload=proposal.payload,
        evidence_doi=proposal.evidence_doi,
        reason=proposal.reason,
        status=proposal.status,
        submitter=proposal.submitter,
        created_at=proposal.created_at,
        updated_at=proposal.updated_at,
    )


@router.get("/proposals/{proposal_id}/reviews", response_model=list[ReviewResponse])
async def get_proposal_reviews(
    proposal_id: int,
    user: Optional[APIKey] = Depends(optional_auth),
):
    """Get all reviews for a proposal."""
    db = get_db()
    proposal = db.get_proposal(proposal_id)
    
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    reviews = db.get_reviews_for_proposal(proposal_id)
    
    return [
        ReviewResponse(
            id=r.id,
            proposal_id=r.proposal_id,
            reviewer=r.reviewer,
            decision=r.decision,
            comment=r.comment,
            created_at=r.created_at,
        )
        for r in reviews
    ]


@router.post("/proposals", status_code=201)
async def create_proposal(
    proposal: ProposalCreate,
    request: Request,
    user: APIKey = Depends(require_role("proposer")),
):
    """
    Create a new tag proposal.
    Requires 'proposer' role or higher.
    """
    db = get_db()
    
    # Validate tag_id format
    if not re.match(r'^[a-z][a-z0-9_]*(\.[a-z0-9_/()+-]+){1,5}$', proposal.tag_id, re.IGNORECASE):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid tag_id format: {proposal.tag_id}"
        )
    
    # Check for duplicate pending proposals
    existing = db.list_proposals(status="pending")
    for p in existing:
        if p.tag_id == proposal.tag_id:
            raise HTTPException(
                status_code=409,
                detail=f"A pending proposal already exists for tag_id: {proposal.tag_id}"
            )
    
    # Create the proposal
    proposal_id = db.create_proposal(
        proposal_type=proposal.proposal_type,
        tag_id=proposal.tag_id,
        canonical_name=proposal.canonical_name,
        payload=proposal.payload,
        evidence_doi=proposal.evidence_doi,
        reason=proposal.reason,
        submitter=user.name,
    )
    
    # Log the action
    db.log_action(
        action="proposal_created",
        user_id=user.name,
        target_type="proposal",
        target_id=str(proposal_id),
        details={"tag_id": proposal.tag_id, "type": proposal.proposal_type},
        ip_address=request.client.host if request.client else None,
    )
    
    return {"id": proposal_id, "status": "pending"}


@router.post("/proposals/{proposal_id}/review", status_code=201)
async def review_proposal(
    proposal_id: int,
    review: ReviewCreate,
    request: Request,
    user: APIKey = Depends(require_role("reviewer")),
):
    """
    Submit a review for a proposal.
    Requires 'reviewer' role or higher.
    
    Uses atomic transaction to prevent race conditions.
    """
    db = get_db()
    
    # Use atomic review to prevent race conditions
    success, message, review_id = db.atomic_review_proposal(
        proposal_id=proposal_id,
        reviewer=user.name,
        decision=review.decision,
        comment=review.comment,
    )
    
    if not success:
        if "not found" in message.lower():
            raise HTTPException(status_code=404, detail=message)
        raise HTTPException(status_code=400, detail=message)
    
    # Determine new status for response
    if review.decision == "approve":
        new_status = "approved"
    elif review.decision == "reject":
        new_status = "rejected"
    else:
        new_status = "pending"  # request_changes keeps it pending
    
    # Log the action
    db.log_action(
        action="proposal_reviewed",
        user_id=user.name,
        target_type="proposal",
        target_id=str(proposal_id),
        details={"decision": review.decision, "new_status": new_status},
        ip_address=request.client.host if request.client else None,
    )
    
    return {
        "review_id": review_id,
        "proposal_id": proposal_id,
        "proposal_status": new_status,
    }


@router.post("/proposals/{proposal_id}/withdraw")
async def withdraw_proposal(
    proposal_id: int,
    request: Request,
    user: APIKey = Depends(require_role("proposer")),
):
    """
    Withdraw a proposal.
    Only the original submitter or admin can withdraw.
    """
    db = get_db()
    
    proposal = db.get_proposal(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    # Check ownership (unless admin)
    if proposal.submitter != user.name and user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only the original submitter or admin can withdraw a proposal"
        )
    
    if proposal.status not in ("pending", "approved"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot withdraw proposal with status '{proposal.status}'"
        )
    
    db.update_proposal_status(proposal_id, "withdrawn")
    
    db.log_action(
        action="proposal_withdrawn",
        user_id=user.name,
        target_type="proposal",
        target_id=str(proposal_id),
        ip_address=request.client.host if request.client else None,
    )
    
    return {"proposal_id": proposal_id, "status": "withdrawn"}


# ============================================================================
# Release Endpoints
# ============================================================================

@router.get("/releases", response_model=list[ReleaseResponse])
async def list_releases(
    limit: int = Query(20, ge=1, le=100),
):
    """List recent releases."""
    db = get_db()
    releases = db.list_releases(limit=limit)
    
    return [
        ReleaseResponse(
            id=r.id,
            version=r.version,
            previous_version=r.previous_version,
            registry_sha256=r.registry_sha256,
            tags_added=r.tags_added,
            tags_removed=r.tags_removed,
            tags_modified=r.tags_modified,
            released_by=r.released_by,
            release_notes=r.release_notes,
            created_at=r.created_at,
        )
        for r in releases
    ]


@router.get("/releases/latest", response_model=Optional[ReleaseResponse])
async def get_latest_release():
    """Get the most recent release."""
    db = get_db()
    release = db.get_latest_release()
    
    if not release:
        return None
    
    return ReleaseResponse(
        id=release.id,
        version=release.version,
        previous_version=release.previous_version,
        registry_sha256=release.registry_sha256,
        tags_added=release.tags_added,
        tags_removed=release.tags_removed,
        tags_modified=release.tags_modified,
        released_by=release.released_by,
        release_notes=release.release_notes,
        created_at=release.created_at,
    )


@router.post("/releases", status_code=201)
async def create_release(
    release: ReleaseCreate,
    request: Request,
    user: APIKey = Depends(require_role("admin")),
):
    """
    Create a new release.
    Requires 'admin' role.
    
    Note: This endpoint records the release in the database.
    The actual release process (validation, contract generation, ZIP creation)
    should be done via the CLI: `python scripts/release.py v0.2.9`
    """
    db = get_db()
    
    # Check for pending proposals
    pending_count = db.count_proposals("pending")
    if pending_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot release with {pending_count} pending proposals. Review all proposals first."
        )
    
    # Get previous version
    latest = db.get_latest_release()
    previous_version = latest.version if latest else None
    
    # Count approved proposals that will be merged
    approved = db.list_proposals(status="approved")
    tags_added = sum(1 for p in approved if p.proposal_type == "new_tag")
    tags_modified = sum(1 for p in approved if p.proposal_type == "modify_tag")
    tags_removed = sum(1 for p in approved if p.proposal_type == "deprecate_tag")
    
    # Record the release
    # Note: registry_sha256 should be computed from actual registry
    # For now, use placeholder
    release_id = db.record_release(
        version=release.version,
        previous_version=previous_version,
        registry_sha256="pending",  # Should be computed
        tags_added=tags_added,
        tags_modified=tags_modified,
        tags_removed=tags_removed,
        released_by=user.name,
        release_notes=release.release_notes,
    )
    
    # Mark approved proposals as merged
    for proposal in approved:
        db.update_proposal_status(proposal.id, "merged")
    
    # Log the action
    db.log_action(
        action="release_created",
        user_id=user.name,
        target_type="release",
        target_id=release.version,
        details={
            "tags_added": tags_added,
            "tags_modified": tags_modified,
            "tags_removed": tags_removed,
            "proposals_merged": len(approved),
        },
        ip_address=request.client.host if request.client else None,
    )
    
    return {
        "release_id": release_id,
        "version": release.version,
        "previous_version": previous_version,
        "proposals_merged": len(approved),
    }


# ============================================================================
# Audit Log Endpoint
# ============================================================================

@router.get("/audit")
async def get_audit_log(
    action: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: APIKey = Depends(require_role("reviewer")),
):
    """
    Get audit log entries.
    Requires 'reviewer' role or higher.
    """
    db = get_db()
    entries = db.get_audit_log(action=action, user_id=user_id, limit=limit, offset=offset)
    
    return [
        {
            "id": e.id,
            "timestamp": e.timestamp,
            "action": e.action,
            "user_id": e.user_id,
            "target_type": e.target_type,
            "target_id": e.target_id,
            "details": e.details,
            "ip_address": e.ip_address,
        }
        for e in entries
    ]
