"""
TRS-602 & TRS-604: Tag validation hook and deprecation warning system.

Provides runtime validation for consumers to ensure they're using valid tags.

Usage:
    from trs_client.validator import TagValidator
    
    validator = TagValidator("http://localhost:8401")
    
    # Validate a tag
    result = validator.validate("env.ae.warm_lighting")
    if result.valid:
        print("Tag is valid")
    if result.deprecated:
        print(f"Warning: Tag deprecated, use {result.replacement}")
    
    # Validate multiple tags
    results = validator.validate_many(["tag1", "tag2", "tag3"])
    
    # Validate as decorator
    @validator.require_valid_tags
    def process_tags(tag_ids: list[str]):
        ...
"""

from __future__ import annotations
import functools
import warnings
from dataclasses import dataclass
from typing import Any, Callable, Optional

from . import TRSClient, TRSError


@dataclass
class ValidationResult:
    """Result of tag validation."""
    tag_id: str
    valid: bool
    exists: bool
    deprecated: bool
    replacement: Optional[str] = None
    message: Optional[str] = None
    
    @property
    def usable(self) -> bool:
        """Tag exists and can be used (even if deprecated)."""
        return self.exists


class DeprecationWarning(UserWarning):
    """Warning for deprecated tags."""
    pass


class TagValidator:
    """
    Validates tags against the TRS registry.
    
    Args:
        base_url: TRS API base URL
        api_key: Optional API key
        warn_deprecated: Emit warnings for deprecated tags
        strict: Raise exception for invalid tags
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:8401",
        api_key: Optional[str] = None,
        warn_deprecated: bool = True,
        strict: bool = False,
    ):
        self.client = TRSClient(base_url=base_url, api_key=api_key)
        self.warn_deprecated = warn_deprecated
        self.strict = strict
        self._tags_cache: Optional[dict] = None
    
    def _get_tags(self) -> dict:
        """Get tags from cache or API."""
        if self._tags_cache is None:
            self._tags_cache = self.client.get_tags()
        return self._tags_cache
    
    def refresh(self) -> None:
        """Refresh the tags cache."""
        self.client.invalidate_cache()
        self._tags_cache = None
    
    def validate(self, tag_id: str) -> ValidationResult:
        """
        Validate a single tag.
        
        Returns ValidationResult with:
        - valid: True if tag exists and is active
        - exists: True if tag exists (may be deprecated)
        - deprecated: True if tag is deprecated
        - replacement: Suggested replacement if deprecated
        """
        tags = self._get_tags()
        
        if tag_id not in tags:
            return ValidationResult(
                tag_id=tag_id,
                valid=False,
                exists=False,
                deprecated=False,
                message=f"Tag not found: {tag_id}",
            )
        
        tag = tags[tag_id]
        
        result = ValidationResult(
            tag_id=tag_id,
            valid=tag.is_active,
            exists=True,
            deprecated=tag.is_deprecated,
            replacement=tag.raw.get("replaced_by") if tag.raw else None,
        )
        
        # Handle deprecation
        if result.deprecated:
            result.message = f"Tag '{tag_id}' is deprecated"
            if result.replacement:
                result.message += f". Use '{result.replacement}' instead"
            
            if self.warn_deprecated:
                warnings.warn(result.message, DeprecationWarning, stacklevel=2)
        
        # Strict mode
        if self.strict and not result.valid:
            raise ValueError(result.message or f"Invalid tag: {tag_id}")
        
        return result
    
    def validate_many(self, tag_ids: list[str]) -> dict[str, ValidationResult]:
        """Validate multiple tags."""
        return {tag_id: self.validate(tag_id) for tag_id in tag_ids}
    
    def is_valid(self, tag_id: str) -> bool:
        """Quick check if tag is valid (active)."""
        return self.validate(tag_id).valid
    
    def exists(self, tag_id: str) -> bool:
        """Quick check if tag exists."""
        return self.validate(tag_id).exists
    
    def get_invalid_tags(self, tag_ids: list[str]) -> list[str]:
        """Get list of invalid tags from a list."""
        results = self.validate_many(tag_ids)
        return [tag_id for tag_id, result in results.items() if not result.valid]
    
    def get_deprecated_tags(self, tag_ids: list[str]) -> list[tuple[str, Optional[str]]]:
        """Get list of deprecated tags with replacements."""
        results = self.validate_many(tag_ids)
        return [
            (tag_id, result.replacement)
            for tag_id, result in results.items()
            if result.deprecated
        ]
    
    # ========================================================================
    # Decorators
    # ========================================================================
    
    def require_valid_tags(self, func: Callable) -> Callable:
        """
        Decorator that validates tag arguments.
        
        Expects function to have a 'tag_ids' or 'tags' parameter.
        
        Usage:
            @validator.require_valid_tags
            def process_tags(tag_ids: list[str]):
                ...
        """
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Find tags parameter
            tag_ids = kwargs.get("tag_ids") or kwargs.get("tags")
            
            if tag_ids:
                if isinstance(tag_ids, str):
                    tag_ids = [tag_ids]
                
                invalid = self.get_invalid_tags(tag_ids)
                if invalid:
                    raise ValueError(f"Invalid tags: {invalid}")
            
            return func(*args, **kwargs)
        
        return wrapper
    
    def warn_deprecated_tags(self, func: Callable) -> Callable:
        """
        Decorator that warns about deprecated tags but doesn't block.
        """
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            tag_ids = kwargs.get("tag_ids") or kwargs.get("tags")
            
            if tag_ids:
                if isinstance(tag_ids, str):
                    tag_ids = [tag_ids]
                
                deprecated = self.get_deprecated_tags(tag_ids)
                for tag_id, replacement in deprecated:
                    msg = f"Tag '{tag_id}' is deprecated"
                    if replacement:
                        msg += f". Consider using '{replacement}'"
                    warnings.warn(msg, DeprecationWarning, stacklevel=2)
            
            return func(*args, **kwargs)
        
        return wrapper


# ============================================================================
# Convenience Functions
# ============================================================================

_default_validator: Optional[TagValidator] = None


def get_validator(
    base_url: str = "http://localhost:8401",
    **kwargs,
) -> TagValidator:
    """Get or create the default validator."""
    global _default_validator
    if _default_validator is None:
        _default_validator = TagValidator(base_url=base_url, **kwargs)
    return _default_validator


def validate_tag(tag_id: str) -> ValidationResult:
    """Validate a tag using the default validator."""
    return get_validator().validate(tag_id)


def is_valid_tag(tag_id: str) -> bool:
    """Check if a tag is valid using the default validator."""
    return get_validator().is_valid(tag_id)
