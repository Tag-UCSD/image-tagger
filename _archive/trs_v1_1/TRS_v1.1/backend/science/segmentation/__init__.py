"""
Semantic segmentation module for architectural region identification.

Provides SegFormer-based segmentation to identify:
- Shell surfaces (ceiling, floor, walls, windows, doors)
- Fixtures and furniture
- Architectural features

Requires: torch, transformers (optional - degrades gracefully)
"""

from .segformer import SegmentationAnalyzer, MockSegmentationAnalyzer

__all__ = ['SegmentationAnalyzer', 'MockSegmentationAnalyzer']
