"""
Localized attribute extraction module.

Provides per-region attribute computation, pooling dense maps to
semantic regions, and contrast metrics between regions.

This is the core implementation of the "localized attribute architecture"
that supersedes the scalar-per-image approach.

Key insight: Humans perceive architectural environments locally, not globally.
Storing only aggregate statistics discards spatial structure that matters
for understanding how built environments affect cognition.
"""

from .region_pooling import RegionPooler, RegionStatistics
from .localized_pipeline import LocalizedAnalyzer

__all__ = ['RegionPooler', 'RegionStatistics', 'LocalizedAnalyzer']
