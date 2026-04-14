# Localized Attribute Integration Package

**Version**: 0.1.0  
**Date**: 2024-12-21  
**Compatibility**: Image Tagger v3.4.74+

---

## Quick Install

```bash
# From your image-tagger repo root (where docker-compose.yml lives):
unzip Neuroarch_Localized_Integration_v0.1.0.zip -d .
```

That's it. The package creates new directories alongside your existing code.

---

## What Gets Added

```
your-repo/
├── backend/science/
│   ├── segmentation/          # NEW - SegFormer semantic segmentation
│   │   ├── __init__.py
│   │   └── segformer.py
│   ├── localized/             # NEW - Per-region attribute extraction
│   │   ├── __init__.py
│   │   ├── region_pooling.py
│   │   └── localized_pipeline.py
│   └── spatial/
│       └── wall_separation.py # NEW - Wall identification algorithm
│
├── contracts/
│   └── localized_image_tags.schema.json  # NEW - JSON Schema
│
└── docs/neuroarch_localized_spec/        # NEW - Design documentation
    ├── README.md
    ├── 01_Core_Specification.md
    ├── 02_Tag_Scope_Classification.md
    ├── 03_Model_Selection_Matrix.md
    ├── 04_Wall_Identification.md
    ├── 05_Prototype_Fractal.md
    └── 06_Implementation_Guide.md
```

---

## Nothing to Delete

This package only **adds** new files. It does not modify your existing code.

Your existing files remain untouched:
- `backend/science/math/fractals.py` - Still works (global fractal D)
- `backend/science/spatial/depth.py` - Still works (ONNX depth)
- `backend/science/pipeline.py` - Still works (unchanged)
- `backend/science/core.py` - Still works (AnalysisFrame)

---

## Dependencies

**Already have** (from your existing setup):
- numpy, scipy, cv2, scikit-image

**New (optional but recommended)**:
```bash
pip install torch transformers
```

Without torch/transformers, the system uses `MockSegmentationAnalyzer`
which provides geometric approximations for testing.

---

## Enabling in Your Pipeline

Edit `backend/science/pipeline.py` to add the new analyzers:

```python
# Add imports at top
from backend.science.segmentation import SegmentationAnalyzer
from backend.science.spatial.wall_separation import WallSeparationAnalyzer
from backend.science.localized import LocalizedAnalyzer

# In SciencePipelineConfig.__init__():
self.enable_localized = False  # Opt-in

# In SciencePipeline.__init__():
self.segmentation = SegmentationAnalyzer()
self.wall_separation = WallSeparationAnalyzer()
self.localized = LocalizedAnalyzer()

# In SciencePipeline.process_image(), after L0 analyzers:
if self.config.enable_localized:
    self.segmentation.analyze(frame)        # Populates segmentation_masks
    self.wall_separation.analyze(frame)     # Populates wall_regions
    self.localized.analyze(frame)           # Computes per-region attributes
```

---

## New Attributes Produced

When `enable_localized=True`, the pipeline produces:

### Per-Region Coverage
```
region.ceiling.coverage     # Fraction of image that is ceiling
region.floor.coverage
region.wall.coverage
region.window.coverage
...
```

### Per-Region Fractal Dimension
```
region.ceiling.fractal_d    # Fractal D computed only for ceiling pixels
region.floor.fractal_d
region.wall.fractal_d
...
```

### Wall Separation
```
wall.count                  # Number of distinct wall surfaces
wall.1.area_fraction        # Per-wall area
wall.1.mean_depth           # Per-wall depth
wall.1.fractal_d            # Per-wall fractal D
...
```

### Contrast Metrics
```
contrast.ceiling_floor.fractal_d    # Ceiling D minus floor D
contrast.wall_ceiling.fractal_d     # Wall D minus ceiling D
contrast.focal_flanking.fractal_d   # Focal wall D minus flanking mean
```

---

## Testing Without GPU

```python
from backend.science.segmentation import MockSegmentationAnalyzer
from backend.science.localized import LocalizedAnalyzer
from backend.science.core import AnalysisFrame
import numpy as np

# Create test frame
image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
frame = AnalysisFrame(image_id=1, original_image=image)

# Run with mock segmentation
seg = MockSegmentationAnalyzer()
seg.analyze(frame)

loc = LocalizedAnalyzer()
loc.analyze(frame)

# Check results
print(frame.attributes)
```

---

## Design Rationale

The `docs/neuroarch_localized_spec/` directory contains the complete
design documentation explaining:

- Why localization matters (01_Core_Specification.md)
- Which attributes need localization (02_Tag_Scope_Classification.md)
- Model selection decisions (03_Model_Selection_Matrix.md)
- Wall separation algorithm (04_Wall_Identification.md)
- Dense fractal computation (05_Prototype_Fractal.md)

---

## Questions?

The implementation follows your existing patterns:
- Analyzers have `analyze(frame)` method
- Results stored via `frame.add_attribute(key, value)`
- Optional dependencies degrade gracefully

See `06_Implementation_Guide.md` for API details.
