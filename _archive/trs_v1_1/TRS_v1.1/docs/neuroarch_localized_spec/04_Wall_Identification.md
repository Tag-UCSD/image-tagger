# Wall Identification Heuristics

**Version**: 0.1.0  
**Date**: 2024-12-21  
**Status**: Draft  
**Parent**: 01_Core_Specification.md  
**Dependencies**: 03_Model_Selection_Matrix.md (SegFormer, Depth Anything V2)

---

## 1. Problem Statement

The specification requires distinguishing **individual walls** within an interior image:
- `wall.N`, `wall.E`, `wall.S`, `wall.W` (compass-based)
- `wall.left`, `wall.right`, `wall.back` (viewpoint-relative)
- `wall.focal`, `wall.flanking` (perceptual salience)

However, semantic segmentation models output a single `wall` class. They do not distinguish wall.1 from wall.2.

**Challenge**: From a single 2D image, segment the unified `wall` mask into distinct wall surfaces.

---

## 2. Available Inputs

| Input | Source | Description |
|-------|--------|-------------|
| `wall_mask` | SegFormer-B5 | Binary mask of all wall pixels |
| `depth_map` | Depth Anything V2 | Relative depth per pixel |
| `ceiling_mask` | SegFormer-B5 | Ceiling region |
| `floor_mask` | SegFormer-B5 | Floor region |
| `window_mask` | SegFormer-B5 | Window regions |
| `rgb_image` | Input | Original image |

---

## 3. Algorithm: Combined Heuristic

### 3.1 Primary: Depth Discontinuity

Different walls are at different depths. Depth discontinuities within the wall mask indicate wall boundaries.

```python
def separate_walls_by_depth(wall_mask, depth_map, threshold=0.15):
    # 1. Compute depth gradient magnitude
    grad_x = sobel(depth_map, axis=1)
    grad_y = sobel(depth_map, axis=0)
    grad_mag = np.sqrt(grad_x**2 + grad_y**2)
    
    # 2. Threshold to find depth edges
    depth_edges = (grad_mag > threshold) & wall_mask
    
    # 3. Split wall mask at edges
    wall_without_edges = wall_mask & ~depth_edges
    
    # 4. Connected component labeling
    labeled_walls = label(wall_without_edges)
    
    return labeled_walls
```

### 3.2 Secondary: Vertical Corner Detection

Wall-to-wall junctions create vertical edges. Detect strong vertical edges within the wall mask.

```python
def refine_with_corners(labeled_walls, rgb_image):
    # 1. Detect edges, filter for near-vertical
    edges = canny(rgb_to_gray(rgb_image))
    orientation = compute_edge_orientation(rgb_image)
    vertical_edges = is_vertical(orientation) & edges
    
    # 2. Find vertical lines via Hough
    lines = hough_lines(vertical_edges)
    
    # 3. Use lines to split ambiguous regions
    return apply_splits(labeled_walls, lines)
```

### 3.3 Tertiary: Color Validation

Validate separation using color consistency within regions.

```python
def validate_with_color(labeled_walls, rgb_image):
    # Check that each labeled region is color-consistent
    # Merge regions with similar color, split heterogeneous regions
    pass
```

---

## 4. Semantic Labeling

Once walls are separated, assign semantic labels.

### 4.1 Viewpoint-Relative Labels

| Label | Definition | Detection |
|-------|------------|-----------|
| `wall.back` | Farthest wall, facing camera | Deepest + largest area |
| `wall.left` | Left side of image | Left half, side-facing |
| `wall.right` | Right side of image | Right half, side-facing |

```python
def assign_viewpoint_labels(labeled_walls, depth_map):
    # Sort walls by depth (deepest first)
    # Deepest large wall → wall.back
    # Remaining by x-position → wall.left, wall.right
```

### 4.2 Perceptual Salience Labels

| Label | Definition | Detection |
|-------|------------|-----------|
| `wall.focal` | Most visually prominent | Highest saliency or contains window |
| `wall.flanking` | Walls beside focal | Adjacent to focal |

```python
def assign_salience_labels(labeled_walls, saliency_map, window_mask):
    # Salience = mean saliency + window bonus
    # Highest salience → wall.focal
    # Others → wall.flanking
```

---

## 5. Edge Cases

### 5.1 Panoramic Views (No Distinct Back Wall)
Rely on corner detection and color clustering when depth is uniform.

### 5.2 Single Visible Wall
Detect and label as `wall.primary`.

### 5.3 Non-Rectilinear Rooms
Use depth + color clustering; don't rely on corner detection.

---

## 6. Module Interface

```python
@dataclass
class WallRegion:
    wall_id: int
    mask: np.ndarray
    viewpoint_label: str        # wall.back, wall.left, etc.
    salience_label: str         # wall.focal, wall.flanking
    mean_depth: float
    area_fraction: float
    contains_windows: bool
    contains_doors: bool

class WallSeparator:
    def separate(
        self,
        wall_mask: np.ndarray,
        depth_map: np.ndarray,
        rgb_image: np.ndarray,
        saliency_map: np.ndarray = None,
        window_mask: np.ndarray = None
    ) -> List[WallRegion]:
        ...
```

---

## 7. Validation

| Metric | Target |
|--------|--------|
| Wall count accuracy | > 90% |
| Wall boundary IoU | > 0.75 |
| Viewpoint label accuracy | > 85% |
| Focal wall accuracy | > 80% |

---

## References

Hedau, V., et al. (2009). Recovering the spatial layout of cluttered rooms. *ICCV*. [~1,200 citations]

Zou, C., et al. (2018). LayoutNet: Reconstructing 3D room layout. *CVPR*. [~500 citations]

---

*End of Wall Identification v0.1.0*
