# Neuroarchitecture Localized Attribute Specification

**Version**: 0.1.0  
**Date**: 2024-12-21  
**Status**: Draft  
**Author**: David Kirsh (UCSD Cognitive Science) with Claude (Anthropic)

---

## Purpose

This package contains the foundational specification for the **Localized Attribute Architecture** of the Neuroarchitecture Image Tagger system. It supersedes the prior scalar-per-image approach and establishes the architectural foundation for spatially-structured feature extraction from interior space images.

**Core insight**: Humans perceive architectural environments locally, not globally. Storing only aggregate statistics discards the spatial structure that matters for understanding how built environments affect cognition.

---

## Directory Structure

```
Neuroarch_Localized_Spec_v0.1.0/
├── README.md                          # This file
├── VERSION                            # Semantic version (0.1.0)
├── demo.py                            # Interactive demo script
│
├── docs/                              # Specification documents
│   ├── 01_Core_Specification.md       # Main schema, vocabulary, storage
│   ├── 02_Tag_Scope_Classification.md # Priority analysis of attributes
│   ├── 03_Model_Selection_Matrix.md   # Pretrained model evaluation
│   ├── 04_Wall_Identification.md      # Wall separation algorithm
│   ├── 05_Prototype_Fractal.md        # Fractal dimension pipeline design
│   └── 06_Implementation_Guide.md     # Python module documentation
│
├── contracts/                         # Schema contracts
│   └── localized_image_tags.schema.json
│
├── examples/                          # Validated examples
│   └── example_localized_tags.json
│
├── src/science/                       # Python implementation (WORKING)
│   ├── models/                        # Model wrappers
│   │   ├── segformer.py               # Semantic segmentation
│   │   └── depth_anything.py          # Depth estimation
│   ├── math/                          # Mathematical operations
│   │   ├── edges.py, fractals.py      # Edge detection, box-counting
│   │   └── fractals_dense.py          # Dense fractal maps
│   ├── perception/                    # Perceptual analysis
│   │   └── region_pooling.py          # Dense-to-region pooling
│   ├── spatial/                       # Spatial analysis
│   │   └── wall_separation.py         # Wall identification
│   └── pipeline/                      # Complete pipelines
│       └── localized_pipeline.py      # Full extraction (main entry)
│
└── archive/                           # Prior context
    └── PROJECT_CONTEXT_HANDOFF_2024-12-21.md
```

---

## Quick Start

```bash
# Install dependencies
pip install numpy scipy scikit-image jsonschema

# Run demo with mock models (no GPU required)
python demo.py --mock

# Output: JSON file conforming to LocalizedImageTags schema
```

```python
from src.science.pipeline.localized_pipeline import LocalizedPipeline, PipelineConfig

config = PipelineConfig(use_mock_models=True)
pipeline = LocalizedPipeline(config)
output = pipeline.process(image, image_id='my_image')

print(f"Ceiling fractal D: {output.region_attributes['ceiling']['fractal_dimension']['value']:.3f}")
```

---

## Documents Summary

### 01_Core_Specification.md
The foundational specification defining:
- Project constitution and non-negotiables
- Semantic region vocabulary (5-level hierarchy)
- Localized attribute schema (TypeScript interfaces)
- Dense map specification
- Contrast/relational metrics framework
- Storage architecture (SQLite + filesystem hybrid)
- Provenance and versioning requirements

### 02_Tag_Scope_Classification.md
Classifies ~129 attributes across 12 taxonomy branches by spatial scope:

| Priority | Count | Description |
|----------|-------|-------------|
| P1 (Must localize) | 67 (52%) | Ecologically invalid without localization |
| P2 (Should localize) | 42 (33%) | Significant information loss |
| P3/P4 | 20 (15%) | Modest benefit or global-only |

**Critical branches**: Visual Complexity (E), Biophilic (H), Prospect-Refuge (D.4), Affective (K)

### 03_Model_Selection_Matrix.md
Evaluates pretrained models across 7 computational domains:

| Domain | Selected Model | Fallback | License |
|--------|----------------|----------|---------|
| Semantic Segmentation | SegFormer-B5 | OneFormer | Apache 2.0 |
| Depth Estimation | Depth Anything V2 (ViT-L) | MiDaS 3.1 | Apache 2.0 |
| Material Recognition | SegFormer + CLIP | Fine-tune OpenSurfaces | Apache 2.0 |
| Saliency | DeepGaze IIE | SAM-ResNet | GPL-3.0 / MIT |

**Estimated pipeline**: ~200ms/image on V100, ~8GB peak memory

### 04_Wall_Identification.md
Specifies algorithm for separating unified `wall` segmentation mask:
- **Primary**: Depth discontinuity detection (Depth Anything V2)
- **Secondary**: Vertical corner detection (Canny + Hough)
- **Tertiary**: Color/texture clustering validation
- **Labeling**: Viewpoint-relative (left/right/back) and salience-based (focal/flanking)

### 05_Prototype_Fractal.md
Complete Python implementation of fractal dimension as paradigm case:
- Dense computation: Sliding window (64×64, stride 8) box-counting
- Region pooling: Mask-weighted statistics per semantic region
- Global aggregation: Area-weighted mean, variance, heterogeneity
- Contrast metrics: ceiling-floor, focal-flanking comparisons
- Validation: Unit tests, integration tests, Kardan et al. benchmark

---

## Key Architectural Decisions

1. **Semantic Region Vocabulary**: 5-level hierarchy (Global → Shell → Features → Fixtures → Transitional) with individual walls distinguished

2. **Tag Scope Classification**: global / per_region / dense_map / relational / hybrid

3. **Storage Architecture**: SQLite (structured queries) + Filesystem (binary dense maps, masks)

4. **Provenance Requirements**: Every computed value records model, version, parameters, timestamp, citation

5. **Wall Separation**: Depth-based primary, corner detection secondary, color validation tertiary

---

## Implementation Phases

| Phase | Weeks | Focus |
|-------|-------|-------|
| 1 | 1-4 | Semantic segmentation, depth estimation, basic color |
| 2 | 5-8 | Complexity (fractal D, edge density, contour entropy) |
| 3 | 9-12 | Biophilic & material (material segmentation, naturalness) |
| 4 | 13-16 | Affect & social (lighting, affective inference, affordances) |
| 5 | 17-20 | Relational & integration (contrasts, harmony, validation) |

---

## Integration with Existing Systems

- **Image Tagger v3.4.74**: This spec supersedes scalar-per-image storage
- **TagRegistry v0.2.8**: 424 attributes to be classified (pending full review)
- **Article Finder v2.2.0**: Literature acquisition for validation
- **Article Eater**: Literature processing for feature operationalization
- **Bayesian Network Repository**: Downstream consumer of localized tags

---

## Validation

```bash
# Validate example against schema
pip install jsonschema
python3 -c "
import json
from jsonschema import Draft202012Validator
with open('contracts/localized_image_tags.schema.json') as f:
    schema = json.load(f)
with open('examples/example_localized_tags.json') as f:
    example = json.load(f)
validator = Draft202012Validator(schema)
errors = list(validator.iter_errors(example))
print('✓ Valid' if not errors else f'✗ {len(errors)} errors')
"
```

---

## Changelog

### v0.1.0 (2024-12-21)
- Initial specification draft
- Core specification with schema, vocabulary, storage architecture
- Tag scope classification (~129 attributes analyzed)
- Model selection matrix (7 domains evaluated)
- Wall identification algorithm specification
- Fractal dimension prototype implementation with Python code
- JSON Schema (Draft 2020-12) with validated example

---

## Open Questions (Future Sessions)

1. **TagRegistry v0.2.8**: Full 424-tag classification pending file review
2. **Resolution trade-offs**: Optimal dense map resolution for storage vs. precision
3. **Confidence thresholds**: Store or filter low-confidence attribute values?
4. **Video support**: Temporal attribute handling for sequences?
5. **Edge cases**: Non-rectilinear rooms, single visible wall scenarios

---

*Generated: Claude session, December 21, 2024*
