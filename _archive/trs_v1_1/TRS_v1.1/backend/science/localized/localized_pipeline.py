"""
Localized attribute analyzer.

Orchestrates per-region attribute extraction:
1. Compute dense attribute maps (fractal D, etc.)
2. Pool to semantic regions (ceiling, floor, walls)
3. Calculate contrast metrics between regions
4. Add localized attributes to AnalysisFrame

This integrates with the existing SciencePipeline as an optional
"L1.5" layer between basic attributes and cognitive VLM.

Usage in pipeline.py:
    if self.config.enable_localized:
        self.localized.analyze(frame)
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, TYPE_CHECKING

import numpy as np
from scipy import ndimage

if TYPE_CHECKING:
    from backend.science.core import AnalysisFrame

from .region_pooling import RegionPooler, RegionStatistics

logger = logging.getLogger(__name__)


class LocalizedAnalyzer:
    """
    Per-region attribute extraction and contrast computation.
    
    Requires that segmentation has already populated:
        - frame.segmentation_masks
        - frame.wall_regions (optional, from WallSeparationAnalyzer)
    
    Also uses frame.edges (from AnalysisFrame.__post_init__).
    """
    
    def __init__(self, window_size: int = 64, stride: int = 8):
        """
        Args:
            window_size: Sliding window for dense map computation
            stride: Step size for sliding window
        """
        self.window_size = window_size
        self.stride = stride
        self.pooler = RegionPooler()
    
    def analyze(self, frame: "AnalysisFrame") -> None:
        """
        Compute localized attributes and contrasts.
        
        Adds to frame:
            - fractal_dense_map: (H', W') dense fractal dimension
            - region.{name}.fractal_d: Per-region fractal dimension
            - contrast.ceiling_floor.fractal_d: Difference metrics
        """
        masks = getattr(frame, 'segmentation_masks', {})
        if not masks:
            logger.warning("LocalizedAnalyzer: no segmentation masks, skipping")
            return
        
        # 1. Compute dense fractal map
        if frame.edges is not None:
            dense_fractal, valid_mask = self._compute_dense_fractal(frame.edges)
            frame.fractal_dense_map = dense_fractal
            frame.fractal_valid_mask = valid_mask
            
            # 2. Pool to regions
            self._pool_fractal_to_regions(frame, dense_fractal, valid_mask)
            
            # 3. Pool to wall regions if available
            self._pool_to_wall_regions(frame, dense_fractal, valid_mask)
        
        # 4. Compute contrasts
        self._compute_contrasts(frame)
    
    def _compute_dense_fractal(
        self,
        edges: np.ndarray
    ) -> tuple:
        """
        Compute dense fractal dimension map using sliding window.
        
        Returns:
            dense_map: (H', W') fractal D values
            valid_mask: (H', W') boolean validity mask
        """
        h, w = edges.shape
        win = self.window_size
        stride = self.stride
        
        # Output dimensions
        out_h = (h - win) // stride + 1
        out_w = (w - win) // stride + 1
        
        if out_h <= 0 or out_w <= 0:
            return np.full((1, 1), np.nan), np.zeros((1, 1), dtype=bool)
        
        D_map = np.full((out_h, out_w), np.nan, dtype=np.float32)
        valid_mask = np.zeros((out_h, out_w), dtype=bool)
        
        for i in range(out_h):
            for j in range(out_w):
                y = i * stride
                x = j * stride
                window = edges[y:y+win, x:x+win]
                
                # Require minimum edge content
                edge_fraction = window.sum() / window.size
                if edge_fraction < 0.01:
                    continue
                
                # Box counting
                D, r_sq = self._box_counting(window)
                
                if r_sq > 0.9 and 0.5 < D < 2.5:
                    D_map[i, j] = D
                    valid_mask[i, j] = True
        
        return D_map, valid_mask
    
    def _box_counting(self, Z: np.ndarray) -> tuple:
        """
        Minkowski-Bouligand (box counting) dimension.
        
        Returns:
            D: Fractal dimension
            r_squared: Regression fit quality
        """
        if Z.sum() == 0:
            return 0.0, 0.0
        
        Z_binary = Z > 0
        p = min(Z.shape)
        n = int(np.floor(np.log(p) / np.log(2)))
        
        if n < 2:
            return 0.0, 0.0
        
        sizes = 2 ** np.arange(n, 1, -1)
        counts = []
        
        for size in sizes:
            # Efficient box counting via reduceat
            try:
                S = np.add.reduceat(
                    np.add.reduceat(
                        Z_binary.astype(int),
                        np.arange(0, Z_binary.shape[0], size),
                        axis=0
                    ),
                    np.arange(0, Z_binary.shape[1], size),
                    axis=1
                )
                count = (S > 0).sum()
            except Exception:
                count = 1
            counts.append(count)
        
        if len(counts) < 2:
            return 0.0, 0.0
        
        # Linear regression on log-log
        log_sizes = np.log(sizes)
        log_counts = np.log(np.array(counts) + 1e-10)
        
        coeffs = np.polyfit(log_sizes, log_counts, 1)
        D = -coeffs[0]
        
        # R-squared
        y_pred = np.polyval(coeffs, log_sizes)
        ss_res = np.sum((log_counts - y_pred) ** 2)
        ss_tot = np.sum((log_counts - np.mean(log_counts)) ** 2)
        r_sq = 1 - (ss_res / (ss_tot + 1e-10))
        
        return float(D), float(r_sq)
    
    def _pool_fractal_to_regions(
        self,
        frame: "AnalysisFrame",
        dense_map: np.ndarray,
        valid_mask: np.ndarray
    ) -> None:
        """Pool dense fractal map to shell regions."""
        masks = getattr(frame, 'segmentation_masks', {})
        
        for region_name, mask in masks.items():
            if not mask.any():
                continue
            
            stats = self.pooler.pool(dense_map, mask, valid_mask)
            
            if not np.isnan(stats.mean):
                frame.add_attribute(
                    f"region.{region_name}.fractal_d",
                    stats.mean
                )
                frame.add_attribute(
                    f"region.{region_name}.fractal_d_std",
                    stats.std
                )
    
    def _pool_to_wall_regions(
        self,
        frame: "AnalysisFrame",
        dense_map: np.ndarray,
        valid_mask: np.ndarray
    ) -> None:
        """Pool to separated wall regions if available."""
        wall_regions = getattr(frame, 'wall_regions', [])
        
        for wall in wall_regions:
            stats = self.pooler.pool(dense_map, wall.mask, valid_mask)
            
            if not np.isnan(stats.mean):
                prefix = f"wall.{wall.wall_id}"
                frame.add_attribute(f"{prefix}.fractal_d", stats.mean)
                frame.add_attribute(f"{prefix}.fractal_d_std", stats.std)
    
    def _compute_contrasts(self, frame: "AnalysisFrame") -> None:
        """Compute contrast metrics between regions."""
        attrs = frame.attributes
        
        # Ceiling-floor fractal contrast
        ceil_fd = attrs.get('region.ceiling.fractal_d')
        floor_fd = attrs.get('region.floor.fractal_d')
        
        if ceil_fd is not None and floor_fd is not None:
            diff = ceil_fd - floor_fd
            frame.add_attribute('contrast.ceiling_floor.fractal_d', diff)
        
        # Wall-ceiling contrast
        wall_fd = attrs.get('region.wall.fractal_d')
        if wall_fd is not None and ceil_fd is not None:
            diff = wall_fd - ceil_fd
            frame.add_attribute('contrast.wall_ceiling.fractal_d', diff)
        
        # Focal vs flanking wall contrast
        wall_regions = getattr(frame, 'wall_regions', [])
        focal_fd = None
        flanking_fds = []
        
        for wall in wall_regions:
            fd = attrs.get(f'wall.{wall.wall_id}.fractal_d')
            if fd is None:
                continue
            
            if wall.salience_label == 'wall.focal':
                focal_fd = fd
            else:
                flanking_fds.append(fd)
        
        if focal_fd is not None and flanking_fds:
            mean_flanking = np.mean(flanking_fds)
            diff = focal_fd - mean_flanking
            frame.add_attribute('contrast.focal_flanking.fractal_d', diff)
