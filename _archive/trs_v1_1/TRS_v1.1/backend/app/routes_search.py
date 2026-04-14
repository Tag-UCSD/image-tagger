"""
TRS-401: Fuzzy search and tag suggestion endpoint.

Provides smart tag search with:
- Fuzzy matching (typo tolerance)
- Alias search
- Domain filtering
- Relevance ranking

Usage:
    GET /api/search?q=light&limit=10
    GET /api/suggest?partial=ill&limit=5
"""

from __future__ import annotations
import re
from difflib import SequenceMatcher
from typing import Optional

from fastapi import APIRouter, Query

from .settings import REGISTRY_DIR
from .registry_loader import load_registry


router = APIRouter(tags=["search"])


def similarity(a: str, b: str) -> float:
    """Calculate string similarity ratio (0.0 to 1.0)."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def fuzzy_match(query: str, text: str, threshold: float = 0.6) -> float:
    """
    Check if query fuzzy-matches text.
    Returns similarity score if above threshold, else 0.
    """
    query = query.lower().strip()
    text = text.lower().strip()
    
    # Exact substring match
    if query in text:
        return 1.0
    
    # Word-level match
    query_words = query.split()
    text_words = text.split()
    
    for qw in query_words:
        for tw in text_words:
            if qw in tw or tw in qw:
                return 0.9
    
    # Fuzzy similarity
    score = similarity(query, text)
    return score if score >= threshold else 0


def search_tags(
    query: str,
    tags: dict,
    limit: int = 20,
    domain: Optional[str] = None,
    status: Optional[str] = None,
) -> list[dict]:
    """
    Search tags with fuzzy matching and ranking.
    
    Returns list of matches with scores.
    """
    query = query.lower().strip()
    results = []
    
    for tag_id, tag in tags.items():
        if not isinstance(tag, dict):
            continue
        
        # Apply filters
        if domain and tag.get("domain") != domain:
            continue
        if status and tag.get("status") != status:
            continue
        
        # Collect searchable text
        searchable = [
            tag_id,
            tag.get("canonical_name", ""),
            tag.get("definition", ""),
        ]
        
        # Add aliases
        semantics = tag.get("semantics", {})
        if isinstance(semantics, dict):
            searchable.extend(semantics.get("aliases", []))
        
        # Add search terms from literature
        literature = tag.get("literature", {})
        if isinstance(literature, dict):
            searchable.extend(literature.get("search_terms", []))
        
        # Calculate best score
        best_score = 0
        match_field = None
        
        for text in searchable:
            if not text:
                continue
            score = fuzzy_match(query, str(text))
            if score > best_score:
                best_score = score
                match_field = text
        
        if best_score > 0:
            results.append({
                "tag_id": tag_id,
                "canonical_name": tag.get("canonical_name"),
                "definition": tag.get("definition", "")[:200],
                "status": tag.get("status"),
                "value_type": tag.get("value_type"),
                "domain": tag.get("domain"),
                "score": round(best_score, 3),
                "match_field": str(match_field)[:50] if match_field else None,
            })
    
    # Sort by score descending
    results.sort(key=lambda x: (-x["score"], x["tag_id"]))
    
    return results[:limit]


def suggest_tags(
    partial: str,
    tags: dict,
    limit: int = 10,
) -> list[dict]:
    """
    Suggest tag IDs based on partial input (autocomplete).
    """
    partial = partial.lower().strip()
    results = []
    
    for tag_id, tag in tags.items():
        if not isinstance(tag, dict):
            continue
        
        # Check tag_id prefix match
        if tag_id.lower().startswith(partial):
            results.append({
                "tag_id": tag_id,
                "canonical_name": tag.get("canonical_name"),
                "match_type": "id_prefix",
            })
            continue
        
        # Check canonical name prefix
        name = tag.get("canonical_name", "").lower()
        if name.startswith(partial):
            results.append({
                "tag_id": tag_id,
                "canonical_name": tag.get("canonical_name"),
                "match_type": "name_prefix",
            })
            continue
        
        # Check word prefix in name
        words = name.split()
        for word in words:
            if word.startswith(partial):
                results.append({
                    "tag_id": tag_id,
                    "canonical_name": tag.get("canonical_name"),
                    "match_type": "word_prefix",
                })
                break
    
    # Sort by match type priority
    priority = {"id_prefix": 0, "name_prefix": 1, "word_prefix": 2}
    results.sort(key=lambda x: (priority.get(x["match_type"], 9), x["tag_id"]))
    
    return results[:limit]


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/search")
async def search(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(20, ge=1, le=100),
    domain: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
):
    """
    Fuzzy search for tags.
    
    Returns ranked results with match scores.
    """
    registry = load_registry(REGISTRY_DIR)
    tags = registry.get("tags", {})
    
    results = search_tags(
        query=q,
        tags=tags,
        limit=limit,
        domain=domain,
        status=status,
    )
    
    return {
        "query": q,
        "count": len(results),
        "results": results,
    }


@router.get("/suggest")
async def suggest(
    partial: str = Query(..., min_length=1, description="Partial tag ID or name"),
    limit: int = Query(10, ge=1, le=50),
):
    """
    Suggest tags for autocomplete.
    
    Returns tag IDs matching the partial input.
    """
    registry = load_registry(REGISTRY_DIR)
    tags = registry.get("tags", {})
    
    results = suggest_tags(
        partial=partial,
        tags=tags,
        limit=limit,
    )
    
    return {
        "partial": partial,
        "count": len(results),
        "suggestions": results,
    }


@router.get("/domains")
async def list_domains():
    """List all unique domains in the registry."""
    registry = load_registry(REGISTRY_DIR)
    tags = registry.get("tags", {})
    
    domains = set()
    for tag in tags.values():
        if isinstance(tag, dict) and tag.get("domain"):
            domains.add(tag["domain"])
    
    return {"domains": sorted(domains)}


@router.get("/stats")
async def registry_stats():
    """Get registry statistics."""
    registry = load_registry(REGISTRY_DIR)
    tags = registry.get("tags", {})
    
    status_counts = {}
    type_counts = {}
    domain_counts = {}
    
    for tag in tags.values():
        if not isinstance(tag, dict):
            continue
        
        status = tag.get("status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
        
        vtype = tag.get("value_type", "unknown")
        type_counts[vtype] = type_counts.get(vtype, 0) + 1
        
        domain = tag.get("domain", "unknown")
        domain_counts[domain] = domain_counts.get(domain, 0) + 1
    
    return {
        "total_tags": len(tags),
        "by_status": status_counts,
        "by_value_type": type_counts,
        "by_domain": domain_counts,
    }
