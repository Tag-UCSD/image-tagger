from pydantic import BaseModel, ConfigDict, Field
from typing import Optional


class ToolConfigUpdate(BaseModel):
    """Contract for modifying AI Model settings.

    ``cost_per_1k_tokens`` must be non-negative; an explicit upper bound
    prevents a typo from bypassing the kill-switch by making a paid
    model effectively free or creating a wildly oversized cost.
    """

    is_enabled: Optional[bool] = None
    cost_per_1k_tokens: Optional[float] = Field(default=None, ge=0.0, le=10_000.0)


class ToolConfigRead(BaseModel):
    """Contract for reading AI Model state"""
    id: int
    name: str
    provider: str
    cost_per_1k_tokens: float
    is_enabled: bool

    model_config = ConfigDict(from_attributes=True)


class BudgetStatus(BaseModel):
    """Contract for Cost Dashboard"""
    total_spent: float
    hard_limit: float
    is_kill_switched: bool