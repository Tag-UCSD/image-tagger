from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class SearchQuery(BaseModel):
    """Contract for Complex Search"""
    query_string: str = ""
    filters: Dict[str, Any] = {}
    page: int = 1
    page_size: int = 20

class ImageSearchResult(BaseModel):
    """Contract for Masonry Grid Items"""
    id: int
    url: str
    tags: List[str]
    meta_data: Dict[str, Any]
    
class ExportRequest(BaseModel):
    """Contract for Dataset Export"""
    image_ids: List[int]
    format: str = "json"
class AttributeRead(BaseModel):
    id: int
    key: str
    name: str
    category: Optional[str] = None
    level: Optional[str] = None
    description: Optional[str] = None
    range: Optional[str] = None
    sources: Optional[str] = None
    notes: Optional[str] = None

    class Config:
        orm_mode = True