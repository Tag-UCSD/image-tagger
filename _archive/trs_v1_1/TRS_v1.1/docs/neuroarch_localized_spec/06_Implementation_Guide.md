# Implementation Guide: Localized Pipeline

**Version**: 0.1.0  
**Date**: 2024-12-21  
**Status**: Working Draft  
**Parent**: 01_Core_Specification.md

---

## 1. Overview

This document describes the implemented Python modules for the localized attribute extraction pipeline. The implementation follows the specifications in docs/01-05 and provides a working prototype that:

- Performs semantic segmentation using SegFormer (or mock)
- Estimates depth using Depth Anything V2 (or mock)
- Separates wall regions using depth discontinuity detection
- Computes fractal dimension (dense map + per-region + global)
- Calculates contrast metrics between regions
- Outputs JSON conforming to the LocalizedImageTags schema

---

## 2. Module Structure

```
src/science/
├── __init__.py
├── models/                    # Pretrained model wrappers
│   ├── __init__.py
│   ├── base.py               # Base classes, provenance
│   ├── segformer.py          # SegFormer semantic segmentation
│   └── depth_anything.py     # Depth Anything V2
├── math/                      # Mathematical operations
│   ├── __init__.py
│   ├── edges.py              # Canny edge detection
│   ├── fractals.py           # Box-counting fractal dimension
│   └── fractals_dense.py     # Dense fractal map computation
├── perception/                # Perceptual analysis
│   ├── __init__.py
│   └── region_pooling.py     # Pool dense maps to regions
├── spatial/                   # Spatial analysis
│   ├── __init__.py
│   └── wall_separation.py    # Wall identification algorithm
└── pipeline/                  # Complete pipelines
    ├── __init__.py
    ├── fractal_pipeline.py   # Fractal-only pipeline
    └── localized_pipeline.py # Full localized extraction
```

---

## 3. Quick Start

### Installation

```bash
# Core dependencies (always required)
pip install numpy scipy scikit-image

# For real models (GPU recommended)
pip install torch transformers

# For schema validation
pip install jsonschema
```

### Basic Usage

```python
from science.pipeline.localized_pipeline import LocalizedPipeline, PipelineConfig

# Configure (use mock models for testing)
config = PipelineConfig(
    use_mock_models=True,  # Set False for real models
    compute_dense_maps=True,
    compute_contrasts=True
)

# Initialize
pipeline = LocalizedPipeline(config)

# Process image
import numpy as np
image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
output = pipeline.process(image, image_id='my_image')

# Access results
print(f"Wall count: {output.global_attributes['wall_count']['value']}")
print(f"Ceiling fractal D: {output.region_attributes['ceiling']['fractal_dimension']['value']}")

# Export to schema-compliant JSON
schema_dict = output.to_schema_dict()
```

### Running the Demo

```bash
# With mock models (no GPU required)
python demo.py --mock

# With real models
python demo.py --image path/to/interior.jpg
```

---

## 4. Model Wrappers

### SegFormerWrapper

```python
from science.models.segformer import SegFormerWrapper

segmenter = SegFormerWrapper(device='cuda', model_size='b5')

# Get all architectural masks
masks = segmenter.get_architectural_masks(image)
# Returns: {'ceiling': array, 'floor': array, 'wall': array, ...}

# Get only shell (primary surfaces)
shell = segmenter.get_shell_masks(image)
# Returns: {'ceiling': array, 'floor': array, 'wall': array, 'window': array, 'door': array}
```

### DepthAnythingWrapper

```python
from science.models.depth_anything import DepthAnythingWrapper

depth_estimator = DepthAnythingWrapper(device='cuda', model_size='large')

result = depth_estimator.predict(image)
depth_map = result.depth_map  # (H, W), 0=near, 1=far

# Get depth edges for wall separation
edges = depth_estimator.get_depth_edges(image, threshold=0.15)
```

### Mock Models

For testing without GPU:

```python
from science.models.segformer import MockSegFormerWrapper
from science.models.depth_anything import MockDepthWrapper

# Same interface, geometric approximations
segmenter = MockSegFormerWrapper()
depth_estimator = MockDepthWrapper()
```

---

## 5. Wall Separation

```python
from science.spatial.wall_separation import WallSeparator, WallSeparatorConfig

config = WallSeparatorConfig(
    depth_threshold=0.12,
    min_wall_area=1000,
    corner_detection=True,
    color_validation=True
)

separator = WallSeparator(config)

wall_regions = separator.separate(
    wall_mask=masks['wall'],
    depth_map=depth_map,
    rgb_image=image,
    window_mask=masks.get('window'),
    door_mask=masks.get('door')
)

for wall in wall_regions:
    print(f"{wall.viewpoint_label}: {wall.area_fraction*100:.1f}% area")
    print(f"  Salience: {wall.salience_label}")
    print(f"  Mean depth: {wall.mean_depth:.3f}")
```

---

## 6. Fractal Analysis

```python
from science.math.fractals_dense import DenseFractalComputer
from science.perception.region_pooling import RegionPooler

# Compute dense fractal map
computer = DenseFractalComputer(window_size=64, stride=8)
result = computer.compute(image)

D_map = result.D_map  # (H/8, W/8) fractal dimension values

# Pool to regions
pooler = RegionPooler()
stats = pooler.pool(D_map, masks['ceiling'], result.valid_mask)

print(f"Ceiling fractal D: {stats.mean:.3f} ± {stats.std:.3f}")
```

---

## 7. Output Schema

The pipeline produces output conforming to `contracts/localized_image_tags.schema.json`:

```python
output = pipeline.process(image)
schema_dict = output.to_schema_dict()

# Contains:
# - image_id, schema_version, computed_at
# - global_attributes: mean_fractal_dimension, wall_count, ...
# - semantic_regions: list of regions with masks and attributes
# - dense_maps: references to dense attribute maps
# - contrast_metrics: ceiling_floor_fractal_diff, ...
# - pipeline_provenance: model versions, execution info
```

---

## 8. Configuration Reference

### PipelineConfig

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `device` | str | 'cuda' | PyTorch device |
| `segformer_size` | str | 'b5' | SegFormer model size |
| `depth_size` | str | 'large' | Depth Anything model size |
| `use_mock_models` | bool | False | Use mock models for testing |
| `fractal_window_size` | int | 64 | Sliding window size |
| `fractal_stride` | int | 8 | Sliding window stride |
| `compute_dense_maps` | bool | True | Generate dense maps |
| `compute_contrasts` | bool | True | Calculate contrast metrics |

### WallSeparatorConfig

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `depth_threshold` | float | 0.12 | Depth gradient threshold |
| `min_wall_area` | int | 1000 | Minimum wall region pixels |
| `corner_detection` | bool | True | Use Hough corner detection |
| `color_validation` | bool | True | Validate with color consistency |

---

## 9. Performance

### With Mock Models (CPU)
- Processing time: ~2 seconds per image
- Memory: ~500 MB

### With Real Models (GPU)
- Processing time: ~0.5 seconds per image
- GPU memory: ~8 GB peak
- Throughput: ~2 images/second

---

## 10. Extending the Pipeline

### Adding New Attributes

1. Create computation module in `science/math/` or `science/perception/`
2. Add to `_compute_region_attributes()` in `localized_pipeline.py`
3. Update schema if needed

### Adding New Models

1. Create wrapper in `science/models/`
2. Inherit from `BaseModelWrapper`
3. Implement `load()`, `predict()`, `get_provenance()`

---

*End of Implementation Guide v0.1.0*
