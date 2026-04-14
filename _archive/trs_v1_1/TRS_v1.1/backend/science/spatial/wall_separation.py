"""
Wall separation algorithm for distinguishing distinct wall surfaces.

Separates unified 'wall' segmentation mask into distinct wall regions
using depth discontinuity detection, vertical corner detection, and
color validation.

This enables per-wall attribute computation (e.g., focal wall vs flanking
walls have different fractal dimensions, colors, etc.)

Integration
-----------
Requires both segmentation masks (wall region) and depth map to function.
If depth is unavailable, returns a single wall region.

References:
    Hedau, V., et al. (2009). Recovering the spatial layout of cluttered rooms. ICCV.
    Zou, C., et al. (2018). LayoutNet: Reconstructing 3D room layout. CVPR.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

import numpy as np
from scipy.ndimage import label, sobel, binary_dilation

if TYPE_CHECKING:
    from backend.science.core import AnalysisFrame

logger = logging.getLogger(__name__)

# Optional: skimage for Hough corner detection
try:
    from skimage.feature import canny
    from skimage.transform import hough_line, hough_line_peaks
    SKIMAGE_HOUGH_AVAILABLE = True
except ImportError:
    SKIMAGE_HOUGH_AVAILABLE = False


@dataclass
class WallRegion:
    """A separated wall region with semantic labels."""
    wall_id: int
    mask: np.ndarray                    # Binary mask (H, W)
    viewpoint_label: str                # wall.back, wall.left, wall.right
    salience_label: str                 # wall.focal, wall.flanking
    mean_depth: float
    area_fraction: float
    centroid: Tuple[float, float]       # (x, y)
    contains_windows: bool = False
    contains_doors: bool = False


@dataclass
class WallSeparatorConfig:
    """Configuration for wall separation algorithm."""
    depth_threshold: float = 0.12       # Depth gradient threshold
    min_wall_area: int = 1000           # Minimum pixels for valid region
    corner_detection: bool = True       # Use Hough vertical corners
    color_validation: bool = True       # Merge by color similarity
    merge_threshold: float = 0.05       # Depth diff threshold for merge


class WallSeparationAnalyzer:
    """
    Separates unified wall mask into distinct wall surfaces.
    
    Algorithm:
    1. Primary: Depth discontinuity detection
    2. Secondary: Vertical corner detection (if skimage available)
    3. Tertiary: Color-based merge validation
    4. Assign semantic labels (back/left/right, focal/flanking)
    
    Usage:
        analyzer = WallSeparationAnalyzer()
        analyzer.analyze(frame)  # Populates frame.wall_regions
    """
    
    def __init__(self, config: WallSeparatorConfig = None):
        self.config = config or WallSeparatorConfig()
    
    def analyze(self, frame: "AnalysisFrame") -> None:
        """
        Separate wall mask into distinct regions.
        
        Requires:
            - frame.segmentation_masks['wall']: Binary wall mask
            - frame.depth_map: Normalized depth (optional but recommended)
        
        Adds to frame:
            - wall_regions: List[WallRegion]
            - wall.count attribute
        """
        masks = getattr(frame, 'segmentation_masks', {})
        wall_mask = masks.get('wall')
        
        if wall_mask is None or not wall_mask.any():
            frame.wall_regions = []
            frame.add_attribute("wall.count", 0)
            return
        
        depth_map = getattr(frame, 'depth_map', None)
        
        # If no depth, return single wall region
        if depth_map is None:
            region = self._single_wall_region(wall_mask, frame)
            frame.wall_regions = [region]
            frame.add_attribute("wall.count", 1)
            return
        
        # Run separation algorithm
        regions = self._separate(
            wall_mask=wall_mask,
            depth_map=depth_map,
            rgb_image=frame.original_image,
            window_mask=masks.get('window'),
            door_mask=masks.get('door')
        )
        
        frame.wall_regions = regions
        frame.add_attribute("wall.count", len(regions))
        
        # Add per-wall attributes
        for wall in regions:
            prefix = f"wall.{wall.wall_id}"
            frame.add_attribute(f"{prefix}.area_fraction", wall.area_fraction)
            frame.add_attribute(f"{prefix}.mean_depth", wall.mean_depth)
    
    def _single_wall_region(self, wall_mask: np.ndarray, frame: "AnalysisFrame") -> WallRegion:
        """Create a single wall region when separation isn't possible."""
        y_coords, x_coords = np.where(wall_mask)
        centroid = (float(x_coords.mean()), float(y_coords.mean()))
        area_fraction = float(wall_mask.sum()) / float(wall_mask.size)
        
        depth_map = getattr(frame, 'depth_map', None)
        mean_depth = float(depth_map[wall_mask].mean()) if depth_map is not None else 0.5
        
        masks = getattr(frame, 'segmentation_masks', {})
        has_windows = 'window' in masks and (wall_mask & masks['window']).any()
        has_doors = 'door' in masks and (wall_mask & masks['door']).any()
        
        return WallRegion(
            wall_id=1,
            mask=wall_mask,
            viewpoint_label='wall.back',
            salience_label='wall.focal',
            mean_depth=mean_depth,
            area_fraction=area_fraction,
            centroid=centroid,
            contains_windows=has_windows,
            contains_doors=has_doors
        )
    
    def _separate(
        self,
        wall_mask: np.ndarray,
        depth_map: np.ndarray,
        rgb_image: np.ndarray,
        window_mask: Optional[np.ndarray] = None,
        door_mask: Optional[np.ndarray] = None
    ) -> List[WallRegion]:
        """Run full separation algorithm."""
        
        # 1. Depth-based separation
        labeled, n_regions = self._depth_separation(wall_mask, depth_map)
        
        # 2. Corner refinement (optional)
        if self.config.corner_detection and SKIMAGE_HOUGH_AVAILABLE:
            labeled = self._refine_with_corners(labeled, rgb_image, wall_mask)
        
        # 3. Color validation / merge
        if self.config.color_validation:
            labeled = self._validate_with_color(labeled, rgb_image)
        
        # 4. Merge small fragments
        labeled = self._merge_small_regions(labeled, depth_map)
        
        # 5. Build WallRegion objects
        regions = self._build_wall_regions(
            labeled, depth_map, rgb_image, window_mask, door_mask
        )
        
        return regions
    
    def _depth_separation(
        self,
        wall_mask: np.ndarray,
        depth_map: np.ndarray
    ) -> Tuple[np.ndarray, int]:
        """Separate walls using depth discontinuities."""
        # Compute depth gradient
        grad_x = sobel(depth_map, axis=1)
        grad_y = sobel(depth_map, axis=0)
        grad_mag = np.sqrt(grad_x**2 + grad_y**2)
        
        # Find depth edges within wall
        depth_edges = (grad_mag > self.config.depth_threshold) & wall_mask
        depth_edges = binary_dilation(depth_edges, iterations=2)
        
        # Remove edges from wall mask and label components
        wall_without_edges = wall_mask & ~depth_edges
        labeled, n_regions = label(wall_without_edges)
        
        return labeled, n_regions
    
    def _refine_with_corners(
        self,
        labeled: np.ndarray,
        rgb_image: np.ndarray,
        wall_mask: np.ndarray
    ) -> np.ndarray:
        """Refine using vertical corner detection."""
        if not SKIMAGE_HOUGH_AVAILABLE:
            return labeled
        
        # Convert to grayscale
        if rgb_image.ndim == 3:
            gray = 0.299 * rgb_image[:,:,0] + 0.587 * rgb_image[:,:,1] + 0.114 * rgb_image[:,:,2]
        else:
            gray = rgb_image.astype(float)
        
        gray = (gray - gray.min()) / (gray.max() - gray.min() + 1e-8)
        
        # Detect edges and filter for vertical
        edges = canny(gray, sigma=1.5)
        grad_x = sobel(gray, axis=1)
        grad_y = sobel(gray, axis=0)
        orientation = np.arctan2(grad_y, grad_x)
        
        tolerance_rad = np.radians(15)
        vertical_mask = (
            (np.abs(orientation - np.pi/2) < tolerance_rad) |
            (np.abs(orientation + np.pi/2) < tolerance_rad)
        )
        vertical_edges = edges & vertical_mask & wall_mask
        
        if not vertical_edges.any():
            return labeled
        
        # Hough transform for strong vertical lines
        try:
            tested_angles = np.linspace(-tolerance_rad, tolerance_rad, 20) + np.pi/2
            h, theta, d = hough_line(vertical_edges, theta=tested_angles)
            accum, angles, dists = hough_line_peaks(h, theta, d, num_peaks=5)
            
            for _, angle, dist in zip(accum, angles, dists):
                y0, y1 = 0, labeled.shape[0]
                x0 = int((dist - y0 * np.sin(angle)) / (np.cos(angle) + 1e-8))
                x1 = int((dist - y1 * np.sin(angle)) / (np.cos(angle) + 1e-8))
                
                x0 = max(0, min(labeled.shape[1]-1, x0))
                x1 = max(0, min(labeled.shape[1]-1, x1))
                
                if abs(x1 - x0) < labeled.shape[1] * 0.1:
                    x_split = (x0 + x1) // 2
                    if 0 < x_split < labeled.shape[1] - 1:
                        labeled = self._split_at_vertical(labeled, x_split, wall_mask)
        except Exception:
            pass
        
        return labeled
    
    def _split_at_vertical(
        self,
        labeled: np.ndarray,
        x_split: int,
        wall_mask: np.ndarray
    ) -> np.ndarray:
        """Split regions crossing a vertical line."""
        for region_id in np.unique(labeled):
            if region_id == 0:
                continue
            
            region_mask = labeled == region_id
            left_pixels = region_mask[:, :x_split].sum()
            right_pixels = region_mask[:, x_split:].sum()
            
            min_side = 0.2 * region_mask.sum()
            if left_pixels > min_side and right_pixels > min_side:
                new_id = labeled.max() + 1
                labeled[region_mask & (np.arange(labeled.shape[1]) >= x_split)] = new_id
        
        return labeled
    
    def _validate_with_color(
        self,
        labeled: np.ndarray,
        rgb_image: np.ndarray
    ) -> np.ndarray:
        """Merge regions with similar colors."""
        region_colors = {}
        for region_id in np.unique(labeled):
            if region_id == 0:
                continue
            mask = labeled == region_id
            if mask.sum() > 0:
                region_colors[region_id] = rgb_image[mask].mean(axis=0)
        
        merged = set()
        new_labeled = labeled.copy()
        
        region_ids = sorted(region_colors.keys())
        for i, id1 in enumerate(region_ids):
            if id1 in merged:
                continue
            for id2 in region_ids[i+1:]:
                if id2 in merged:
                    continue
                
                color_diff = np.linalg.norm(region_colors[id1] - region_colors[id2])
                
                if color_diff < 20:
                    mask1 = new_labeled == id1
                    mask2 = new_labeled == id2
                    dilated1 = binary_dilation(mask1, iterations=3)
                    
                    if (dilated1 & mask2).any():
                        new_labeled[new_labeled == id2] = id1
                        merged.add(id2)
        
        return self._relabel_consecutive(new_labeled)
    
    def _relabel_consecutive(self, labeled: np.ndarray) -> np.ndarray:
        """Relabel with consecutive IDs starting from 1."""
        unique_ids = [x for x in np.unique(labeled) if x > 0]
        new_labeled = np.zeros_like(labeled)
        for new_id, old_id in enumerate(unique_ids, start=1):
            new_labeled[labeled == old_id] = new_id
        return new_labeled
    
    def _merge_small_regions(
        self,
        labeled: np.ndarray,
        depth_map: np.ndarray
    ) -> np.ndarray:
        """Merge small fragments into nearest large region."""
        new_labeled = labeled.copy()
        
        region_sizes = {}
        region_depths = {}
        for region_id in np.unique(labeled):
            if region_id == 0:
                continue
            mask = labeled == region_id
            region_sizes[region_id] = mask.sum()
            region_depths[region_id] = depth_map[mask].mean()
        
        small_regions = [
            rid for rid, size in region_sizes.items()
            if size < self.config.min_wall_area
        ]
        large_regions = [
            rid for rid, size in region_sizes.items()
            if size >= self.config.min_wall_area
        ]
        
        for small_id in small_regions:
            if not large_regions:
                break
            
            small_depth = region_depths[small_id]
            closest_id = min(
                large_regions,
                key=lambda rid: abs(region_depths[rid] - small_depth)
            )
            new_labeled[new_labeled == small_id] = closest_id
        
        return self._relabel_consecutive(new_labeled)
    
    def _build_wall_regions(
        self,
        labeled: np.ndarray,
        depth_map: np.ndarray,
        rgb_image: np.ndarray,
        window_mask: Optional[np.ndarray],
        door_mask: Optional[np.ndarray]
    ) -> List[WallRegion]:
        """Build WallRegion objects with semantic labels."""
        regions = []
        total_wall_area = (labeled > 0).sum()
        h, w = labeled.shape
        
        region_info = []
        for region_id in np.unique(labeled):
            if region_id == 0:
                continue
            
            mask = labeled == region_id
            y_coords, x_coords = np.where(mask)
            
            region_info.append({
                'id': region_id,
                'mask': mask,
                'area': mask.sum(),
                'area_fraction': mask.sum() / total_wall_area if total_wall_area > 0 else 0,
                'centroid': (float(x_coords.mean()), float(y_coords.mean())),
                'mean_depth': float(depth_map[mask].mean()),
                'has_windows': window_mask is not None and (mask & window_mask).any(),
                'has_doors': door_mask is not None and (mask & door_mask).any(),
            })
        
        # Assign viewpoint labels
        viewpoint_labels = self._assign_viewpoint_labels(region_info, h, w)
        salience_labels = self._assign_salience_labels(region_info)
        
        for info in region_info:
            rid = info['id']
            regions.append(WallRegion(
                wall_id=rid,
                mask=info['mask'],
                viewpoint_label=viewpoint_labels.get(rid, f'wall.{rid}'),
                salience_label=salience_labels.get(rid, 'wall.flanking'),
                mean_depth=info['mean_depth'],
                area_fraction=info['area_fraction'],
                centroid=info['centroid'],
                contains_windows=info['has_windows'],
                contains_doors=info['has_doors']
            ))
        
        return regions
    
    def _assign_viewpoint_labels(
        self,
        region_info: List[dict],
        img_height: int,
        img_width: int
    ) -> Dict[int, str]:
        """Assign viewpoint labels (back/left/right)."""
        labels = {}
        if not region_info:
            return labels
        
        # Deepest wall with area > 15% is back wall
        sorted_info = sorted(region_info, key=lambda x: (-x['mean_depth'], -x['area']))
        back_candidates = [i for i in sorted_info if i['area_fraction'] > 0.15]
        
        if back_candidates:
            back_wall = back_candidates[0]
            labels[back_wall['id']] = 'wall.back'
            remaining = [i for i in region_info if i['id'] != back_wall['id']]
        else:
            remaining = region_info
        
        # Left/right by x centroid
        center_x = img_width / 2
        for info in remaining:
            if info['id'] in labels:
                continue
            cx = info['centroid'][0]
            if cx < center_x * 0.7:
                labels[info['id']] = 'wall.left'
            elif cx > center_x * 1.3:
                labels[info['id']] = 'wall.right'
            else:
                labels[info['id']] = 'wall.center'
        
        return labels
    
    def _assign_salience_labels(self, region_info: List[dict]) -> Dict[int, str]:
        """Assign salience labels (focal/flanking)."""
        labels = {}
        if not region_info:
            return labels
        
        # Windows boost salience
        for info in region_info:
            info['salience'] = 0.5 + (0.3 if info['has_windows'] else 0.0)
        
        sorted_info = sorted(region_info, key=lambda x: -x['salience'])
        
        if sorted_info:
            labels[sorted_info[0]['id']] = 'wall.focal'
            for info in sorted_info[1:]:
                labels[info['id']] = 'wall.flanking'
        
        return labels
