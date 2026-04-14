"""
Region pooling: aggregate dense maps to semantic regions.

Given a dense attribute map (e.g., fractal dimension at every pixel)
and a binary mask for a region (e.g., ceiling), compute summary
statistics for that region.

Handles resolution mismatch between dense maps and segmentation masks.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
from scipy.ndimage import zoom


@dataclass
class RegionStatistics:
    """Statistics for a single region from a dense map."""
    mean: float
    std: float
    median: float
    min: float
    max: float
    p25: float
    p75: float
    count: int          # Number of valid pixels
    coverage: float     # Fraction of region with valid values
    
    def to_dict(self) -> dict:
        return {
            'mean': self.mean,
            'std': self.std,
            'median': self.median,
            'min': self.min,
            'max': self.max,
            'p25': self.p25,
            'p75': self.p75,
            'count': self.count,
            'coverage': self.coverage,
        }


class RegionPooler:
    """
    Pool dense attribute maps to region-level statistics.
    
    Usage:
        pooler = RegionPooler()
        stats = pooler.pool(fractal_map, ceiling_mask)
        print(f"Ceiling fractal D: {stats.mean:.3f} ± {stats.std:.3f}")
    """
    
    def pool(
        self,
        dense_map: np.ndarray,
        region_mask: np.ndarray,
        valid_mask: Optional[np.ndarray] = None
    ) -> RegionStatistics:
        """
        Compute statistics for dense_map within region_mask.
        
        Args:
            dense_map: (H, W) or (H', W') dense attribute values
            region_mask: (H, W) binary mask for the region
            valid_mask: (H', W') optional mask of valid dense values
            
        Returns:
            RegionStatistics with mean, std, median, etc.
        """
        # Handle resolution mismatch
        if dense_map.shape != region_mask.shape:
            # Resize region_mask to match dense_map
            scale_h = dense_map.shape[0] / region_mask.shape[0]
            scale_w = dense_map.shape[1] / region_mask.shape[1]
            region_mask_resized = zoom(
                region_mask.astype(np.float32),
                (scale_h, scale_w),
                order=1  # Bilinear
            ) > 0.5
        else:
            region_mask_resized = region_mask
        
        # Combine with valid mask
        if valid_mask is not None:
            combined_mask = region_mask_resized & valid_mask
        else:
            combined_mask = region_mask_resized & ~np.isnan(dense_map)
        
        # Extract values
        values = dense_map[combined_mask]
        
        if len(values) == 0:
            return RegionStatistics(
                mean=float('nan'),
                std=float('nan'),
                median=float('nan'),
                min=float('nan'),
                max=float('nan'),
                p25=float('nan'),
                p75=float('nan'),
                count=0,
                coverage=0.0
            )
        
        # Compute statistics
        region_area = region_mask_resized.sum()
        coverage = len(values) / region_area if region_area > 0 else 0.0
        
        return RegionStatistics(
            mean=float(np.mean(values)),
            std=float(np.std(values)),
            median=float(np.median(values)),
            min=float(np.min(values)),
            max=float(np.max(values)),
            p25=float(np.percentile(values, 25)),
            p75=float(np.percentile(values, 75)),
            count=len(values),
            coverage=coverage
        )
    
    def pool_all_regions(
        self,
        dense_map: np.ndarray,
        masks: dict,
        valid_mask: Optional[np.ndarray] = None
    ) -> dict:
        """
        Pool dense map to all regions in masks dict.
        
        Args:
            dense_map: Dense attribute map
            masks: Dict[str, np.ndarray] of region masks
            valid_mask: Optional validity mask
            
        Returns:
            Dict[str, RegionStatistics]
        """
        results = {}
        for region_name, mask in masks.items():
            if mask.any():
                results[region_name] = self.pool(dense_map, mask, valid_mask)
        return results
