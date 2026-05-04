from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from backend.schemas.common import TimestampSchema

# --- INPUT SCHEMAS (Frontend -> Backend) ---

class ValidationRequest(BaseModel):
    """
    Payload sent when a Tagger presses 'Confirm' or uses a keyboard shortcut.

    All free-text fields are capped (Task A-4) so request validation
    rejects pathological inputs at the boundary instead of letting them
    flow into the database.
    """
    image_id: int = Field(ge=1)
    attribute_key: str = Field(
        max_length=200,
        description="e.g. 'spatial.prospect'",
    )
    value: float = Field(ge=0.0, le=1.0, description="Normalized value 0-1")
    duration_ms: int = Field(
        ge=0,
        le=24 * 60 * 60 * 1000,
        description="Time spent looking at image (velocity tracking, capped at 24h)",
    )

class RegionCreateRequest(BaseModel):
    """
    Payload sent when a Tagger draws a box or polygon.
    """
    image_id: int = Field(ge=1)
    geometry: Dict[str, Any] = Field(description="GeoJSON or {x,y,w,h}")
    manual_label: str = Field(
        max_length=200,
        description="Human assigned class",
    )

# --- OUTPUT SCHEMAS (Backend -> Frontend) ---

class ImageWorkItem(TimestampSchema):
    """
    The 'Next Image' payload. Optimized for the Workbench Canvas.
    """
    id: int
    filename: str
    # Pre-signed URL or local path served via Nginx
    url: str 
    # Context for the tagger (e.g. "Is this Modern?")
    meta_data: Dict[str, Any] = {} 

class ValidationResponse(TimestampSchema):
    id: int
    status: str = "success"
    agreement_score: Optional[float] = None # Calculated async if other validators exist