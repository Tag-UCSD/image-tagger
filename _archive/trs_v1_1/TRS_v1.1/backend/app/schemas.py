"""
TRS-706: Request validation schemas.

Provides strict Pydantic models for API request validation.
"""

from __future__ import annotations
import re
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ============================================================================
# Tag Schemas
# ============================================================================

class TagIdMixin:
    """Mixin for tag ID validation."""
    
    @field_validator("tag_id", mode="before")
    @classmethod
    def validate_tag_id(cls, v: str) -> str:
        if not v:
            raise ValueError("tag_id cannot be empty")
        
        if len(v) > 200:
            raise ValueError("tag_id too long (max 200 characters)")
        
        # Check for path traversal
        if ".." in v or "\\" in v:
            raise ValueError("Invalid characters in tag_id")
        
        # Validate format
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z0-9_/()+-]+){1,5}$', v):
            raise ValueError("Invalid tag_id format")
        
        return v


class TagPayload(BaseModel):
    """Schema for tag data in proposals."""
    
    canonical_name: Optional[str] = Field(None, max_length=200)
    category: Optional[str] = Field(None, max_length=100)
    value_type: Optional[str] = Field(None, pattern="^(ordinal|binary|continuous|categorical|nominal|interval|ratio)$")
    status: Optional[str] = Field(None, pattern="^(active|deprecated|experimental|proposed|reserved|obsolete)$")
    domain: Optional[str] = Field(None, max_length=200)
    subdomain: Optional[str] = Field(None, max_length=200)
    definition: Optional[str] = Field(None, max_length=5000)
    
    extractability: Optional[dict] = None
    semantics: Optional[dict] = None
    literature: Optional[dict] = None
    bn: Optional[dict] = None
    
    class Config:
        extra = "allow"  # Allow additional fields


# ============================================================================
# Proposal Schemas
# ============================================================================

class ProposalCreateRequest(BaseModel, TagIdMixin):
    """Request schema for creating a proposal."""
    
    proposal_type: str = Field(..., pattern="^(new_tag|modify_tag|deprecate_tag)$")
    tag_id: str = Field(..., min_length=3, max_length=200)
    canonical_name: Optional[str] = Field(None, max_length=200)
    payload: dict = Field(...)
    evidence_doi: Optional[str] = Field(None, max_length=500)
    reason: Optional[str] = Field(None, max_length=2000)
    
    @field_validator("evidence_doi", mode="before")
    @classmethod
    def validate_doi(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        
        # Basic DOI format check
        if v.startswith("https://doi.org/") or v.startswith("http://dx.doi.org/"):
            return v
        if re.match(r'^10\.\d{4,}/.+$', v):
            return f"https://doi.org/{v}"
        
        return v  # Allow other URLs


class ReviewCreateRequest(BaseModel):
    """Request schema for creating a review."""
    
    decision: str = Field(..., pattern="^(approve|reject|request_changes)$")
    comment: Optional[str] = Field(None, max_length=5000)
    
    @model_validator(mode="after")
    def validate_comment_required(self) -> "ReviewCreateRequest":
        if self.decision == "reject" and not self.comment:
            raise ValueError("Comment is required for rejection")
        if self.decision == "request_changes" and not self.comment:
            raise ValueError("Comment is required when requesting changes")
        return self


# ============================================================================
# Release Schemas
# ============================================================================

class ReleaseCreateRequest(BaseModel):
    """Request schema for creating a release."""
    
    version: str = Field(..., pattern="^v[0-9]+\\.[0-9]+\\.[0-9]+$")
    release_notes: Optional[str] = Field(None, max_length=10000)
    
    @field_validator("version", mode="before")
    @classmethod
    def validate_version(cls, v: str) -> str:
        if not v.startswith("v"):
            raise ValueError("Version must start with 'v'")
        
        parts = v[1:].split(".")
        if len(parts) != 3:
            raise ValueError("Version must be in format vX.Y.Z")
        
        try:
            for part in parts:
                int(part)
        except ValueError:
            raise ValueError("Version parts must be integers")
        
        return v


# ============================================================================
# Search Schemas
# ============================================================================

class SearchRequest(BaseModel):
    """Request schema for search queries."""
    
    q: str = Field(..., min_length=1, max_length=200)
    limit: int = Field(20, ge=1, le=100)
    domain: Optional[str] = Field(None, max_length=200)
    status: Optional[str] = Field(None, pattern="^(active|deprecated|experimental)$")
    
    @field_validator("q", mode="before")
    @classmethod
    def sanitize_query(cls, v: str) -> str:
        # Remove dangerous characters
        v = re.sub(r'[<>"\']', '', v)
        return v.strip()


class SuggestRequest(BaseModel):
    """Request schema for autocomplete suggestions."""
    
    partial: str = Field(..., min_length=1, max_length=100)
    limit: int = Field(10, ge=1, le=50)


# ============================================================================
# API Key Schemas
# ============================================================================

class APIKeyCreateRequest(BaseModel):
    """Request schema for creating an API key."""
    
    name: str = Field(..., min_length=1, max_length=100)
    role: str = Field(..., pattern="^(admin|reviewer|proposer|viewer)$")
    expires_in_days: Optional[int] = Field(None, ge=1, le=365)
    
    @field_validator("name", mode="before")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        # Remove potentially dangerous characters
        v = re.sub(r'[<>"\'/\\]', '', v)
        return v.strip()


# ============================================================================
# Batch Import Schemas
# ============================================================================

class BatchImportTag(BaseModel, TagIdMixin):
    """Schema for a tag in batch import."""
    
    tag_id: str = Field(..., min_length=3, max_length=200)
    canonical_name: str = Field(..., max_length=200)
    value_type: str = Field(..., pattern="^(ordinal|binary|continuous|categorical)$")
    status: str = Field("proposed", pattern="^(active|deprecated|experimental|proposed)$")
    domain: Optional[str] = Field(None, max_length=200)
    definition: Optional[str] = Field(None, max_length=5000)


class BatchImportRequest(BaseModel):
    """Request schema for batch import."""
    
    tags: list[BatchImportTag] = Field(..., min_length=1, max_length=100)
    submitter: str = Field(..., min_length=1, max_length=200)
    
    @field_validator("tags")
    @classmethod
    def check_unique_tag_ids(cls, v: list[BatchImportTag]) -> list[BatchImportTag]:
        tag_ids = [t.tag_id for t in v]
        if len(tag_ids) != len(set(tag_ids)):
            raise ValueError("Duplicate tag_ids in batch")
        return v
