"""
TRS-605: Example Image Tagger integration.

Shows how to integrate TRS client into the Image Tagger consumer.

This module demonstrates:
- Loading contract at startup
- Validating predictions against contract
- Handling deprecated tags
- Contract caching and refresh
"""

from __future__ import annotations
import logging
from typing import Any, Optional

from trs_client import TRSClient, Contract
from trs_client.compliance import ContractChecker, ComplianceReport
from trs_client.validator import TagValidator

logger = logging.getLogger(__name__)


class ImageTaggerTRSIntegration:
    """
    TRS integration for the Image Tagger.
    
    Usage:
        trs = ImageTaggerTRSIntegration("http://trs-api:8401")
        
        # At startup
        trs.load_contract()
        
        # Before prediction
        valid_tags = trs.filter_predictions(predicted_tags)
        
        # Check compliance
        report = trs.audit_session(all_used_tags)
    """
    
    CONSUMER_NAME = "image_tagger"
    
    def __init__(
        self,
        trs_url: str = "http://localhost:8401",
        api_key: Optional[str] = None,
        strict_mode: bool = False,
    ):
        """
        Initialize TRS integration.
        
        Args:
            trs_url: TRS API URL
            api_key: Optional API key
            strict_mode: Raise on contract violations
        """
        self.trs_url = trs_url
        self.strict_mode = strict_mode
        
        # Initialize clients
        self.client = TRSClient(trs_url, api_key=api_key)
        self.checker = ContractChecker(trs_url, self.CONSUMER_NAME, api_key=api_key)
        self.validator = TagValidator(trs_url, api_key=api_key, warn_deprecated=True)
        
        # State
        self._contract: Optional[Contract] = None
        self._allowed_tags: set[str] = set()
        self._tag_to_info: dict[str, dict] = {}
        self._extractable_tags: set[str] = set()
    
    def load_contract(self) -> Contract:
        """
        Load the image_tagger contract.
        
        Call this at startup to cache the contract.
        """
        logger.info(f"Loading TRS contract for {self.CONSUMER_NAME}...")
        
        self._contract = self.client.get_contract(self.CONSUMER_NAME)
        
        # Build lookup structures
        self._allowed_tags = set(self._contract.get_tag_ids())
        self._tag_to_info = {
            t.get("tag_id"): t
            for t in self._contract.tags
            if t.get("tag_id")
        }
        
        # Find extractable tags
        self._extractable_tags = set()
        for tag in self._contract.tags:
            tag_id = tag.get("tag_id")
            extract = tag.get("extractability", {})
            if extract.get("from_2d") == "yes":
                self._extractable_tags.add(tag_id)
        
        logger.info(
            f"Loaded contract v{self._contract.version}: "
            f"{len(self._allowed_tags)} tags, "
            f"{len(self._extractable_tags)} extractable from 2D"
        )
        
        return self._contract
    
    def refresh_contract(self) -> Contract:
        """Refresh the contract from TRS."""
        self.checker.refresh()
        self.validator.refresh()
        return self.load_contract()
    
    @property
    def contract(self) -> Contract:
        """Get the loaded contract."""
        if self._contract is None:
            self.load_contract()
        return self._contract
    
    def is_extractable(self, tag_id: str) -> bool:
        """Check if a tag can be extracted from 2D images."""
        return tag_id in self._extractable_tags
    
    def get_extractable_tags(self) -> list[str]:
        """Get all tags that can be extracted from 2D."""
        return list(self._extractable_tags)
    
    def get_tag_info(self, tag_id: str) -> Optional[dict]:
        """Get contract info for a tag."""
        return self._tag_to_info.get(tag_id)
    
    def filter_predictions(
        self,
        predictions: dict[str, Any],
        remove_deprecated: bool = False,
    ) -> dict[str, Any]:
        """
        Filter predictions to only contract-allowed tags.
        
        Args:
            predictions: Dict of tag_id -> prediction value
            remove_deprecated: Also remove deprecated tags
        
        Returns:
            Filtered predictions dict
        """
        filtered = {}
        removed = []
        deprecated = []
        
        for tag_id, value in predictions.items():
            if tag_id not in self._allowed_tags:
                removed.append(tag_id)
                continue
            
            info = self._tag_to_info.get(tag_id, {})
            if info.get("status") == "deprecated":
                deprecated.append(tag_id)
                if remove_deprecated:
                    continue
            
            filtered[tag_id] = value
        
        # Log warnings
        if removed:
            logger.warning(f"Removed {len(removed)} tags not in contract: {removed[:5]}...")
        if deprecated:
            logger.warning(f"Using {len(deprecated)} deprecated tags: {deprecated[:5]}...")
        
        # Strict mode
        if self.strict_mode and removed:
            raise ValueError(f"Tags not in contract: {removed}")
        
        return filtered
    
    def validate_prediction_schema(
        self,
        predictions: dict[str, Any],
    ) -> list[str]:
        """
        Validate prediction values against expected types.
        
        Returns list of validation errors.
        """
        errors = []
        
        for tag_id, value in predictions.items():
            info = self._tag_to_info.get(tag_id)
            if not info:
                continue
            
            value_type = info.get("value_type")
            
            # Basic type validation
            if value_type == "binary":
                if not isinstance(value, (bool, int)) or value not in (0, 1, True, False):
                    errors.append(f"{tag_id}: expected binary, got {type(value).__name__}")
            
            elif value_type == "ordinal":
                if not isinstance(value, (int, float)):
                    errors.append(f"{tag_id}: expected numeric, got {type(value).__name__}")
            
            elif value_type == "continuous":
                if not isinstance(value, (int, float)):
                    errors.append(f"{tag_id}: expected numeric, got {type(value).__name__}")
        
        return errors
    
    def audit_session(
        self,
        used_tags: list[str],
        check_coverage: bool = False,
    ) -> ComplianceReport:
        """
        Audit a tagging session for compliance.
        
        Args:
            used_tags: All tags used in the session
            check_coverage: Check for unused contract tags
        """
        return self.checker.audit(used_tags, check_coverage=check_coverage)
    
    def get_replacement(self, deprecated_tag: str) -> Optional[str]:
        """Get replacement for a deprecated tag."""
        info = self._tag_to_info.get(deprecated_tag)
        if info:
            return info.get("replaced_by")
        return None
    
    def health_check(self) -> dict:
        """Check TRS connectivity and contract status."""
        try:
            healthy = self.client.health()
            contract_loaded = self._contract is not None
            
            return {
                "trs_healthy": healthy,
                "contract_loaded": contract_loaded,
                "contract_version": self._contract.version if self._contract else None,
                "allowed_tags": len(self._allowed_tags),
                "extractable_tags": len(self._extractable_tags),
            }
        except Exception as e:
            return {
                "trs_healthy": False,
                "error": str(e),
            }


# ============================================================================
# Usage Example
# ============================================================================

def example_usage():
    """Example of how to use the integration."""
    
    # Initialize at startup
    trs = ImageTaggerTRSIntegration("http://localhost:8401")
    trs.load_contract()
    
    # Get extractable tags for model
    extractable = trs.get_extractable_tags()
    print(f"Model should predict {len(extractable)} tags")
    
    # After prediction
    raw_predictions = {
        "env.ae.warm_lighting": 0.8,
        "env.ae.high_illuminance": 0.6,
        "invalid_tag": 0.5,  # Not in contract
    }
    
    # Filter to contract
    valid_predictions = trs.filter_predictions(raw_predictions)
    print(f"Valid predictions: {valid_predictions}")
    
    # Validate types
    errors = trs.validate_prediction_schema(valid_predictions)
    if errors:
        print(f"Schema errors: {errors}")
    
    # End of session audit
    used_tags = list(valid_predictions.keys())
    report = trs.audit_session(used_tags)
    print(f"Compliant: {report.compliant}, Warnings: {report.warning_count}")


if __name__ == "__main__":
    example_usage()
