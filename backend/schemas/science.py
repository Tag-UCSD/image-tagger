"""
Response schemas for science / ML pipeline outputs (Phase 1, Task A-7).

``SciencePayload`` is the canonical wire format returned alongside an
image record. Every feature is a ``TrustEnvelope[float]``; affordance
predictions carry their own envelope on the ``score``. There is
deliberately NO separate ``confidence`` map for features — the envelope
*is* the confidence record. ``extra="forbid"`` enforces this at the
schema layer so a future regression that re-introduces a parallel
``confidence`` map fails validation rather than silently shipping.

See ``/docs/CONTRACT.md`` § "SciencePayload" for the canonical shape.
"""

from __future__ import annotations

from typing import Dict, List, Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.science.trust import TrustEnvelope

RunStatus = Literal["pending", "running", "completed", "failed"]


class AffordancePrediction(BaseModel):
    """One row of the affordance results table.

    The ``confidence`` envelope wraps the same numeric value as ``score``;
    keeping both at the top level lets the frontend display the score in
    UI tables without parsing the envelope, while still carrying the
    full provenance for the trust badge.
    """

    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=1)
    label: str = Field(min_length=1)
    score: float
    confidence: TrustEnvelope[float]


class SciencePayload(BaseModel):
    """Canonical science block returned with image records.

    ``features`` is a map keyed by canonical feature keys. Each value is
    the trust envelope for that feature's numeric output. There is no
    separate ``confidence`` map for features; the envelope carries the
    confidence interval directly.
    """

    model_config = ConfigDict(extra="forbid")

    run_id: int = Field(ge=0)
    run_status: RunStatus
    features: Dict[str, TrustEnvelope[float]] = Field(default_factory=dict)
    affordances: List[AffordancePrediction] = Field(default_factory=list)
