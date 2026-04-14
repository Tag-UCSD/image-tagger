# Prototype Implementation: Fractal Dimension Pipeline

**Version**: 0.1.0  
**Date**: 2024-12-21  
**Status**: Draft  
**Parent**: 01_Core_Specification.md  
**Code**: src/science/

---

## 1. Purpose

This document specifies the **complete implementation** of fractal dimension as the paradigm case for the localized pipeline. Fractal dimension is chosen because:

1. **Theoretically validated**: Kardan et al. (2015) established edge-based fractal D as predictor of naturalness preference
2. **Hybrid scope**: Requires all three levels (dense map → per-region → global)
3. **Computationally tractable**: Box-counting is well-understood
4. **Scientifically important**: Central to visual complexity assessment

---

## 2. Theoretical Foundation

### 2.1 Fractal Dimension in Environmental Psychology

Fractal dimension (D) measures complexity of edge patterns. For natural scenes, D typically ranges from 1.3-1.5; for man-made scenes, 1.5-1.7 (Spehar et al., 2003).

**Key findings**:
- Preference peaks at intermediate D (~1.3-1.5) for natural scenes
- Naturalness perception correlates negatively with D (Kardan et al., 2015)
- Architectural complexity can be characterized by D

### 2.2 Box-Counting Method

1. Convert image to edge map (Canny)
2. Overlay grids of decreasing box sizes (ε)
3. Count boxes containing edge pixels (N(ε))
4. Fit: D = slope of log(N) vs log(1/ε)

---

## 3. Pipeline Architecture

```
Input Image → Edge Detection → Dense Fractal Map → Region Pooling → Global Aggregation → Contrast Metrics → Output
```

**Stages**:
1. **Edge Detection**: Canny edge detection (σ=1.0)
2. **Dense Computation**: Sliding window (64×64, stride 8) box-counting
3. **Region Pooling**: Mask-weighted statistics per semantic region
4. **Global Aggregation**: Area-weighted mean across regions
5. **Contrast Metrics**: ceiling-floor, focal-flanking differences

---

## 4. Code Modules

### 4.1 Edge Detection (`src/science/math/edges.py`)

```python
class EdgeDetector:
    def __init__(self, sigma=1.0, auto_threshold=True):
        self.sigma = sigma
        self.auto_threshold = auto_threshold
    
    def detect(self, image: np.ndarray) -> np.ndarray:
        """Detect edges. Returns binary edge map."""
        gray = rgb_to_gray(image)
        return canny(gray, sigma=self.sigma)
```

### 4.2 Box-Counting (`src/science/math/fractals.py`)

```python
@dataclass
class FractalResult:
    D: float              # Fractal dimension
    r_squared: float      # Goodness of fit
    scales: List[int]
    counts: List[int]

class BoxCountingFractal:
    def __init__(self, scales=[2, 4, 8, 16, 32]):
        self.scales = scales
    
    def compute(self, edge_map: np.ndarray) -> FractalResult:
        counts = []
        for scale in self.scales:
            count = self._count_boxes(edge_map, scale)
            counts.append(count)
        
        # Fit log-log relationship
        slope, _, r_value, _, _ = linregress(
            np.log(1/np.array(self.scales)),
            np.log(np.array(counts))
        )
        
        return FractalResult(D=slope, r_squared=r_value**2, ...)
    
    def _count_boxes(self, edge_map, box_size):
        # Reshape and count boxes with any edge pixel
        boxes = edge_map.reshape(h//box_size, box_size, w//box_size, box_size)
        return boxes.any(axis=(1,3)).sum()
```

### 4.3 Dense Computation (`src/science/math/fractals_dense.py`)

```python
@dataclass
class DenseFractalMap:
    D_map: np.ndarray        # (H', W') values
    r2_map: np.ndarray       # Fit quality
    resolution: Tuple[int, int]
    window_size: int
    stride: int

class DenseFractalComputer:
    def __init__(self, window_size=64, stride=8):
        self.window_size = window_size
        self.stride = stride
        self.fractal = BoxCountingFractal()
    
    def compute(self, image: np.ndarray) -> DenseFractalMap:
        edges = EdgeDetector().detect(image)
        
        # Slide window and compute local D
        for i, j in grid_positions(edges, self.window_size, self.stride):
            window = edges[i:i+ws, j:j+ws]
            result = self.fractal.compute(window)
            D_map[i//stride, j//stride] = result.D
        
        return DenseFractalMap(D_map=D_map, ...)
```

### 4.4 Region Pooling (`src/science/perception/region_pooling.py`)

```python
@dataclass
class RegionStatistics:
    mean: float
    std: float
    median: float
    min: float
    max: float
    coverage: float

class RegionPooler:
    def pool(self, dense_map, region_mask) -> RegionStatistics:
        # Resize mask to match dense map resolution
        mask_resized = resize(region_mask, dense_map.shape)
        values = dense_map[mask_resized]
        
        return RegionStatistics(
            mean=np.mean(values),
            std=np.std(values),
            ...
        )
```

### 4.5 Global Aggregation (`src/science/perception/aggregation.py`)

```python
class GlobalAggregator:
    def aggregate(self, region_stats, region_areas) -> GlobalStatistics:
        # Area-weighted mean
        total_area = sum(region_areas.values())
        weighted_mean = sum(
            stats.mean * area / total_area
            for stats, area in zip(region_stats.values(), region_areas.values())
        )
        
        return GlobalStatistics(mean=weighted_mean, variance=np.var(means), ...)
```

### 4.6 Contrast Metrics (`src/science/perception/contrasts.py`)

```python
class ContrastComputer:
    def compute_standard_contrasts(self, stats):
        contrasts = []
        
        if 'ceiling' in stats and 'floor' in stats:
            contrasts.append(ContrastMetric(
                metric_id='ceiling_floor_fractal_diff',
                value=stats['ceiling'].mean - stats['floor'].mean
            ))
        
        return contrasts
```

### 4.7 Pipeline Orchestration (`src/science/pipeline/fractal_pipeline.py`)

```python
class FractalDimensionPipeline:
    def run(self, image, region_masks):
        # 1. Dense fractal map
        dense = DenseFractalComputer().compute(image)
        
        # 2. Pool to regions
        region_stats = RegionPooler().pool_all(dense.D_map, region_masks)
        
        # 3. Global aggregation
        global_stats = GlobalAggregator().aggregate(region_stats)
        
        # 4. Contrasts
        contrasts = ContrastComputer().compute_standard_contrasts(region_stats)
        
        return {
            'dense_map': dense,
            'region_stats': region_stats,
            'global_stats': global_stats,
            'contrasts': contrasts
        }
```

---

## 5. Usage Example

```python
from src.science.pipeline.fractal_pipeline import FractalDimensionPipeline

image = np.array(Image.open('interior.jpg'))
region_masks = get_segmentation_masks(image)

pipeline = FractalDimensionPipeline()
result = pipeline.run(image, region_masks)

print(f"Global mean D: {result['global_stats'].mean:.3f}")
print(f"Ceiling D: {result['region_stats']['ceiling'].mean:.3f}")
print(f"Floor D: {result['region_stats']['floor'].mean:.3f}")
print(f"Contrast: {result['contrasts'][0].value:.3f}")
```

---

## 6. Validation

### Unit Tests
- Known fractal patterns (Sierpinski: D≈1.89)
- Line has D≈1, filled square has D≈2
- Empty returns NaN

### Integration Tests
- Full pipeline on sample images
- Output structure validation
- Values in expected range (1.0 < D < 2.0)

### Benchmark Validation
- Compare against Kardan et al. (2015) reported values
- Natural scenes: D ≈ 1.3-1.5
- Man-made scenes: D ≈ 1.5-1.7

---

## 7. Performance

| Stage | Time | Memory |
|-------|------|--------|
| Edge detection | 10 ms | H×W |
| Dense fractal | 150 ms | H×W + output |
| Region pooling | 5 ms | negligible |
| Global/contrasts | <1 ms | negligible |
| **Total** | **~170 ms** | — |

---

## 8. Extension Pattern

This prototype establishes the pattern for other hybrid attributes:

| Attribute | Dense | Pool | Contrast |
|-----------|-------|------|----------|
| Edge density | Sliding Canny ratio | Mean/region | Ceiling-floor |
| Luminance | Per-pixel | Mean, std | Ratio |
| Depth | Depth Anything | Mean/region | Prospect-refuge |

---

## References

Kardan, O., et al. (2015). Is the preference of natural versus man-made scenes driven by bottom-up processing? *Frontiers in Psychology*, 6, 471.

Spehar, B., et al. (2003). Universal aesthetic of fractals. *Computers & Graphics*, 27(5), 813-820.

---

*End of Prototype Implementation v0.1.0*
