"""
Trust envelope for ML and feature outputs (Phase 1, Task A-7).

Every science feature and ML prediction returned by the API is wrapped in
a `TrustEnvelope` declaring its evaluation status. Features without
registry metadata default to ``evaluation_status = "untested"`` so the
frontend renders an honest "not validated" badge until evidence exists.

See ``/docs/CONTRACT.md`` § "ML Model I/O Contract" for the canonical
shape. Phase 1 establishes the *mechanism* for honest trust display; the
evidence-collection workstream that promotes envelopes from ``untested``
to ``proxy_validated`` or ``validated`` is deferred to follow-up work.
"""

from __future__ import annotations

from typing import Any, Generic, Literal, Optional, Tuple, TypeVar

from pydantic import BaseModel, ConfigDict, Field

EvaluationStatus = Literal["validated", "proxy_validated", "untested"]

T = TypeVar("T")


class TrustEnvelope(BaseModel, Generic[T]):
    """Generic envelope wrapping a science output with provenance metadata.

    All fields except ``confidence_interval_95`` are required. The
    frontend must honor ``evaluation_status == "untested"`` with a
    visible warning badge per the contract.
    """

    model_config = ConfigDict(extra="forbid")

    value: T
    model_id: str = Field(min_length=1)
    evaluation_status: EvaluationStatus
    confidence_interval_95: Optional[Tuple[float, float]] = None
    n_training: int = Field(ge=0)
    notes: str = ""


# Sentinel model_id used for outputs that have no registry entry. Kept as
# a constant so a Phase 2 audit can grep this exact string when collecting
# evidence gaps.
LEGACY_MODEL_ID = "legacy.unregistered_v0"

DEFAULT_UNTESTED_NOTES = (
    "No evaluation provenance recorded in the feature registry; "
    "defaults to untested per Phase 1 trust contract."
)


def untested_envelope(
    value: Any,
    *,
    model_id: str = LEGACY_MODEL_ID,
    notes: str = DEFAULT_UNTESTED_NOTES,
) -> TrustEnvelope:
    """Build an envelope for a feature with no registry metadata.

    The contract requires every science output to carry a trust envelope.
    For legacy features whose evaluation provenance has not yet been
    documented, this helper produces a uniform "untested" envelope so the
    UI never has to guess a default.
    """
    return TrustEnvelope(
        value=value,
        model_id=model_id,
        evaluation_status="untested",
        confidence_interval_95=None,
        n_training=0,
        notes=notes,
    )
