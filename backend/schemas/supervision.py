from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict


class TaggerPerformance(BaseModel):
    """Aggregate tagger stats (historical aggregate shape).

    Canonical ``GET /v1/monitor/velocity`` returns :class:`MonitorVelocitySeriesResponse`
    (/docs/CONTRACT.md).
    """

    user_id: int
    username: str
    images_validated: int
    avg_duration_ms: int
    status: str = "active"

    model_config = ConfigDict(from_attributes=True)


class IRRStat(BaseModel):
    """Legacy per-image/overlap IRR row (historical heatmaps)."""

    image_id: int
    filename: str
    attribute_key: str
    agreement_score: float
    conflict_count: int
    raters: List[str]

    model_config = ConfigDict(from_attributes=True)


class VelocityPoint(BaseModel):
    """UTC hourly bucket counts for validations (CONTRACT velocity)."""

    timestamp: str
    count: int


class MonitorVelocitySeriesResponse(BaseModel):
    series: List[VelocityPoint]


class MonitorIRRRow(BaseModel):
    """Aggregated IRR row per registry attribute (/docs/CONTRACT.md § Monitor)."""

    attribute_key: str
    attribute_name: str
    irr: float
    bin: Literal["low", "medium", "high"]
    n_pairs: int


class MonitorIRRTableResponse(BaseModel):
    rows: List[MonitorIRRRow]


class ValidationDetail(BaseModel):
    """Per-validation record for the Tag Inspector drawer."""

    id: int
    user_id: Optional[int] = None
    username: Optional[str] = None
    image_id: int
    attribute_key: str
    value: float
    duration_ms: Optional[int] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)