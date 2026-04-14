"""
TRS-603: Contract compliance checker.

Verifies that consumers are using tags according to their contract.

Usage:
    from trs_client.compliance import ContractChecker
    
    checker = ContractChecker("http://localhost:8401", "image_tagger")
    
    # Check if tags are in contract
    result = checker.check_tags(["tag1", "tag2"])
    
    # Validate full compliance
    report = checker.audit(used_tags, config)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional

from . import TRSClient, Contract, TRSError


@dataclass
class ComplianceViolation:
    """A contract compliance violation."""
    tag_id: str
    violation_type: str  # not_in_contract, wrong_type, deprecated
    message: str
    severity: str = "error"  # error, warning, info


@dataclass
class ComplianceReport:
    """Result of a compliance audit."""
    consumer: str
    contract_version: str
    tags_checked: int
    valid_tags: int
    violations: list[ComplianceViolation] = field(default_factory=list)
    
    @property
    def compliant(self) -> bool:
        """True if no errors."""
        return not any(v.severity == "error" for v in self.violations)
    
    @property
    def error_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == "error")
    
    @property
    def warning_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == "warning")


class ContractChecker:
    """
    Checks compliance with a consumer contract.
    
    Args:
        base_url: TRS API base URL
        consumer: Consumer name (e.g., "image_tagger")
        api_key: Optional API key
    """
    
    def __init__(
        self,
        base_url: str,
        consumer: str,
        api_key: Optional[str] = None,
    ):
        self.client = TRSClient(base_url=base_url, api_key=api_key)
        self.consumer = consumer
        self._contract: Optional[Contract] = None
        self._contract_tags: Optional[set[str]] = None
        self._tag_info: Optional[dict[str, dict]] = None
    
    def _load_contract(self) -> Contract:
        """Load or return cached contract."""
        if self._contract is None:
            self._contract = self.client.get_contract(self.consumer)
            self._contract_tags = set(self._contract.get_tag_ids())
            self._tag_info = {
                t.get("tag_id"): t
                for t in self._contract.tags
                if t.get("tag_id")
            }
        return self._contract
    
    def refresh(self) -> None:
        """Refresh the contract cache."""
        self._contract = None
        self._contract_tags = None
        self._tag_info = None
    
    @property
    def contract(self) -> Contract:
        """Get the contract."""
        return self._load_contract()
    
    @property
    def allowed_tags(self) -> set[str]:
        """Get set of allowed tag IDs."""
        self._load_contract()
        return self._contract_tags or set()
    
    def is_allowed(self, tag_id: str) -> bool:
        """Check if a tag is in the contract."""
        return tag_id in self.allowed_tags
    
    def get_tag_info(self, tag_id: str) -> Optional[dict]:
        """Get contract info for a tag."""
        self._load_contract()
        return self._tag_info.get(tag_id) if self._tag_info else None
    
    def check_tags(self, tag_ids: list[str]) -> list[ComplianceViolation]:
        """
        Check a list of tags against the contract.
        
        Returns list of violations.
        """
        violations = []
        
        for tag_id in tag_ids:
            if not self.is_allowed(tag_id):
                violations.append(ComplianceViolation(
                    tag_id=tag_id,
                    violation_type="not_in_contract",
                    message=f"Tag '{tag_id}' is not in the {self.consumer} contract",
                    severity="error",
                ))
                continue
            
            # Check for deprecation
            info = self.get_tag_info(tag_id)
            if info and info.get("status") == "deprecated":
                replacement = info.get("replaced_by")
                msg = f"Tag '{tag_id}' is deprecated"
                if replacement:
                    msg += f". Use '{replacement}'"
                violations.append(ComplianceViolation(
                    tag_id=tag_id,
                    violation_type="deprecated",
                    message=msg,
                    severity="warning",
                ))
        
        return violations
    
    def audit(
        self,
        used_tags: list[str],
        check_coverage: bool = False,
    ) -> ComplianceReport:
        """
        Perform a full compliance audit.
        
        Args:
            used_tags: List of tag IDs being used
            check_coverage: Also check for unused contract tags
        """
        contract = self.contract
        violations = self.check_tags(used_tags)
        
        # Check coverage
        if check_coverage:
            used_set = set(used_tags)
            unused = self.allowed_tags - used_set
            
            # Just informational for now
            for tag_id in unused:
                violations.append(ComplianceViolation(
                    tag_id=tag_id,
                    violation_type="unused",
                    message=f"Contract tag '{tag_id}' is not being used",
                    severity="info",
                ))
        
        return ComplianceReport(
            consumer=self.consumer,
            contract_version=contract.version,
            tags_checked=len(used_tags),
            valid_tags=len(used_tags) - sum(
                1 for v in violations
                if v.violation_type == "not_in_contract"
            ),
            violations=violations,
        )
    
    def assert_compliant(self, tag_ids: list[str]) -> None:
        """
        Assert that tags are contract-compliant.
        
        Raises ValueError if not compliant.
        """
        violations = self.check_tags(tag_ids)
        errors = [v for v in violations if v.severity == "error"]
        
        if errors:
            messages = [v.message for v in errors]
            raise ValueError(f"Contract violations: {messages}")
    
    def filter_allowed(self, tag_ids: list[str]) -> list[str]:
        """Filter tag list to only contract-allowed tags."""
        return [t for t in tag_ids if self.is_allowed(t)]
    
    def filter_disallowed(self, tag_ids: list[str]) -> list[str]:
        """Get tags that are not in the contract."""
        return [t for t in tag_ids if not self.is_allowed(t)]


# ============================================================================
# Convenience Functions
# ============================================================================

def check_contract_compliance(
    base_url: str,
    consumer: str,
    tag_ids: list[str],
) -> ComplianceReport:
    """Quick compliance check."""
    checker = ContractChecker(base_url, consumer)
    return checker.audit(tag_ids)
