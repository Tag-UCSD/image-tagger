"""
TRS Python Client Library

A simple client for interacting with the Tag Registry Service API.

Installation:
    pip install trs-client  # (future)
    # or
    pip install -e clients/python/

Usage:
    from trs_client import TRSClient
    
    client = TRSClient("http://localhost:8401")
    
    # Get registry
    registry = client.get_registry()
    
    # Search tags
    results = client.search("lighting", limit=10)
    
    # Get tag by ID
    tag = client.get_tag("env.ae.warm_lighting")
    
    # Get contract
    contract = client.get_contract("image_tagger")
"""

from __future__ import annotations
import json
from dataclasses import dataclass
from typing import Any, Optional
from urllib.parse import urljoin

import httpx


@dataclass
class Tag:
    """Represents a tag from the registry."""
    tag_id: str
    canonical_name: str
    status: str
    value_type: str
    domain: Optional[str] = None
    definition: Optional[str] = None
    extractability: Optional[dict] = None
    raw: Optional[dict] = None
    
    @classmethod
    def from_dict(cls, tag_id: str, data: dict) -> "Tag":
        return cls(
            tag_id=tag_id,
            canonical_name=data.get("canonical_name", ""),
            status=data.get("status", "unknown"),
            value_type=data.get("value_type", "unknown"),
            domain=data.get("domain"),
            definition=data.get("definition"),
            extractability=data.get("extractability"),
            raw=data,
        )
    
    @property
    def is_active(self) -> bool:
        return self.status == "active"
    
    @property
    def is_deprecated(self) -> bool:
        return self.status == "deprecated"
    
    @property
    def extractable_from_2d(self) -> bool:
        if not self.extractability:
            return False
        return self.extractability.get("from_2d") == "yes"


@dataclass
class SearchResult:
    """Represents a search result."""
    tag_id: str
    canonical_name: str
    score: float
    status: Optional[str] = None
    value_type: Optional[str] = None


@dataclass
class Contract:
    """Represents a consumer contract."""
    consumer: str
    version: str
    registry_sha256: str
    tags: list[dict]
    
    @property
    def tag_count(self) -> int:
        return len(self.tags)
    
    def get_tag_ids(self) -> list[str]:
        """Get all tag IDs in this contract."""
        return [t.get("tag_id") for t in self.tags if t.get("tag_id")]


class TRSError(Exception):
    """Base exception for TRS client errors."""
    pass


class TRSConnectionError(TRSError):
    """Connection error."""
    pass


class TRSAPIError(TRSError):
    """API returned an error."""
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"API error {status_code}: {detail}")


class TRSClient:
    """
    Client for the Tag Registry Service API.
    
    Args:
        base_url: TRS API base URL (e.g., "http://localhost:8401")
        api_key: Optional API key for authenticated requests
        timeout: Request timeout in seconds
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:8401",
        api_key: Optional[str] = None,
        timeout: float = 30.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._client = httpx.Client(timeout=timeout)
        self._registry_cache: Optional[dict] = None
    
    def _headers(self) -> dict:
        """Get request headers."""
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers
    
    def _request(self, method: str, path: str, **kwargs) -> Any:
        """Make an HTTP request."""
        url = f"{self.base_url}{path}"
        
        try:
            response = self._client.request(
                method,
                url,
                headers=self._headers(),
                **kwargs,
            )
        except httpx.RequestError as e:
            raise TRSConnectionError(f"Connection error: {e}")
        
        if response.status_code >= 400:
            try:
                detail = response.json().get("detail", response.text)
            except Exception:
                detail = response.text
            raise TRSAPIError(response.status_code, detail)
        
        return response.json()
    
    def _get(self, path: str, params: Optional[dict] = None) -> Any:
        return self._request("GET", path, params=params)
    
    def _post(self, path: str, json: Optional[dict] = None) -> Any:
        return self._request("POST", path, json=json)
    
    # ========================================================================
    # Health & Status
    # ========================================================================
    
    def health(self) -> bool:
        """Check if the API is healthy."""
        try:
            result = self._get("/health")
            return result.get("ok", False)
        except TRSError:
            return False
    
    def status(self) -> dict:
        """Get API status and registry info."""
        return self._get("/status")
    
    # ========================================================================
    # Registry
    # ========================================================================
    
    def get_registry(self, use_cache: bool = True) -> dict:
        """
        Get the full registry.
        
        Args:
            use_cache: Use cached registry if available
        """
        if use_cache and self._registry_cache:
            return self._registry_cache
        
        registry = self._get("/registry")
        self._registry_cache = registry
        return registry
    
    def get_tags(self) -> dict[str, Tag]:
        """Get all tags as Tag objects."""
        registry = self.get_registry()
        tags_data = registry.get("tags", {})
        
        return {
            tag_id: Tag.from_dict(tag_id, data)
            for tag_id, data in tags_data.items()
            if isinstance(data, dict)
        }
    
    def get_tag(self, tag_id: str) -> Optional[Tag]:
        """Get a specific tag by ID."""
        tags = self.get_tags()
        return tags.get(tag_id)
    
    def invalidate_cache(self) -> None:
        """Clear the registry cache."""
        self._registry_cache = None
    
    # ========================================================================
    # Search
    # ========================================================================
    
    def search(
        self,
        query: str,
        limit: int = 20,
        domain: Optional[str] = None,
        status: Optional[str] = None,
    ) -> list[SearchResult]:
        """
        Search for tags.
        
        Args:
            query: Search query
            limit: Maximum results
            domain: Filter by domain
            status: Filter by status
        """
        params = {"q": query, "limit": limit}
        if domain:
            params["domain"] = domain
        if status:
            params["status"] = status
        
        result = self._get("/api/search", params=params)
        
        return [
            SearchResult(
                tag_id=r.get("tag_id", ""),
                canonical_name=r.get("canonical_name", ""),
                score=r.get("score", 0),
                status=r.get("status"),
                value_type=r.get("value_type"),
            )
            for r in result.get("results", [])
        ]
    
    def suggest(self, partial: str, limit: int = 10) -> list[str]:
        """Get autocomplete suggestions."""
        result = self._get("/api/suggest", params={"partial": partial, "limit": limit})
        return [s.get("tag_id") for s in result.get("suggestions", [])]
    
    # ========================================================================
    # Contracts
    # ========================================================================
    
    def get_contract(self, consumer: str) -> Contract:
        """
        Get a consumer contract.
        
        Args:
            consumer: Consumer name (e.g., "image_tagger")
        """
        result = self._get("/contracts/latest", params={"consumer": consumer})
        
        meta = result.get("meta", {})
        
        return Contract(
            consumer=consumer,
            version=meta.get("contract_version", ""),
            registry_sha256=meta.get("registry_sha256", ""),
            tags=result.get("tags", []),
        )
    
    # ========================================================================
    # Stats
    # ========================================================================
    
    def stats(self) -> dict:
        """Get registry statistics."""
        return self._get("/api/stats")
    
    def domains(self) -> list[str]:
        """Get all unique domains."""
        result = self._get("/api/domains")
        return result.get("domains", [])
    
    # ========================================================================
    # Context Manager
    # ========================================================================
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()
    
    def close(self):
        """Close the HTTP client."""
        self._client.close()


# ============================================================================
# Convenience Functions
# ============================================================================

def create_client(
    base_url: str = "http://localhost:8401",
    api_key: Optional[str] = None,
) -> TRSClient:
    """Create a TRS client instance."""
    return TRSClient(base_url=base_url, api_key=api_key)
