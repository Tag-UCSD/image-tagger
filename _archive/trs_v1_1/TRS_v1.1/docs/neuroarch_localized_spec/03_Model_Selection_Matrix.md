# Model Selection Matrix for Neuroarchitecture Image Tagger

**Version**: 0.1.0  
**Date**: 2024-12-21  
**Status**: Draft  
**Parent**: 01_Core_Specification.md

---

## 1. Purpose

This document evaluates pretrained models for each computational domain required by the Localized Attribute Architecture. Selection criteria include accuracy, architectural relevance, output format compatibility, computational cost, licensing, and maintenance status.

---

## 2. Domain Overview

| Domain | Unlocks Attributes | Priority | Selected Model |
|--------|-------------------|----------|----------------|
| Semantic Segmentation | All per-region | CRITICAL | SegFormer-B5 |
| Depth Estimation | Prospect-refuge, spatial | CRITICAL | Depth Anything V2 |
| Material Recognition | Branch G, naturalness | HIGH | SegFormer + CLIP |
| Lighting Estimation | Branch A | HIGH | Luminance analysis |
| Saliency/Attention | Cognitive load | MEDIUM | DeepGaze IIE |
| Affective Inference | Branch K | MEDIUM | Feature-based |
| Room Layout | Spatial configuration | MEDIUM | Depth-based |

---

## 3. Semantic Segmentation

### Selected: SegFormer-B5

| Attribute | Value |
|-----------|-------|
| **Architecture** | Transformer encoder, MLP decoder |
| **Training data** | ADE20K (150 classes) |
| **mIoU (ADE20K)** | 51.0% |
| **Inference speed** | ~25 FPS on V100 |
| **License** | Apache 2.0 |
| **HuggingFace** | nvidia/segformer-b5-finetuned-ade-640-640 |

**Rationale**: Best speed/accuracy tradeoff. Apache 2.0 license. Excellent HuggingFace ecosystem support. Can scale to B2/B3 for faster processing if needed.

**Fallback**: OneFormer (MIT, 57.0% mIoU, ~8 FPS) if instance segmentation becomes critical.

---

## 4. Depth Estimation

### Selected: Depth Anything V2 (ViT-L)

| Attribute | Value |
|-----------|-------|
| **Architecture** | DINOv2 encoder, DPT decoder |
| **Training data** | 62M synthetic + real images |
| **Metrics** | δ1 > 0.99 on NYU Depth V2 |
| **Inference speed** | ~30 FPS on V100 |
| **License** | Apache 2.0 |
| **Repository** | DepthAnything/Depth-Anything-V2 |

**Rationale**: State-of-the-art monocular depth. Excellent indoor scene performance. Sharp depth boundaries critical for prospect-refuge. Multiple size variants.

**Note**: Outputs relative depth (sufficient for prospect-refuge comparisons). ZoeDepth available if metric depth needed.

---

## 5. Material Recognition

### Selected: Hybrid (SegFormer + CLIP)

**Approach**:
1. Use SegFormer ADE20K for material-related classes (wood floor, carpet, tile, brick, glass, concrete)
2. Add CLIP zero-shot classification for finer material distinctions
3. Future: Train material head on OpenSurfaces if CLIP insufficient

**Rationale**: Leverage existing segmentation. CLIP provides flexible zero-shot classification without additional model. Reduces pipeline complexity.

---

## 6. Saliency/Attention

### Selected: DeepGaze IIE

| Attribute | Value |
|-----------|-------|
| **Architecture** | VGG features + learned readout |
| **Training data** | MIT1003, SALICON, eye-tracking |
| **License** | GPL-3.0 |
| **Repository** | matthias-k/DeepGaze |

**Alternative**: SAM-ResNet (MIT license) if GPL unacceptable.

**Rationale**: Most accurate saliency model. Trained on actual eye-tracking data. Can toggle center bias.

---

## 7. Affective Inference

### Selected: Feature-based approach

**Approach**: Use validated low-level correlates rather than direct affect prediction:
- Color saturation → arousal (Valdez & Mehrabian, 1994)
- Brightness → valence (Lakens et al., 2013)
- Complexity (fractal D) → arousal (Spehar et al., 2015)

**Future**: Fine-tune EMOTIC for architectural affect if feature-based insufficient.

**Rationale**: Direct affect prediction from scenes less validated. Our complexity, color, and lighting attributes already capture affect-relevant variance.

---

## 8. Room Layout / Wall Separation

### Selected: Depth-based detection

**Approach**:
1. Use Depth Anything V2 depth map
2. Detect depth discontinuities → wall boundaries
3. Use semantic segmentation wall class → wall regions
4. Combine for wall identification

**Rationale**: Already running depth and segmentation. Dedicated layout models (LayoutNet, HorizonNet) add complexity and assume specific viewpoints.

---

## 9. Computational Requirements

### Per-Image Pipeline

| Model | GPU Memory | Inference Time |
|-------|------------|----------------|
| SegFormer-B5 | 4 GB | 40 ms |
| Depth Anything V2 (ViT-L) | 6 GB | 33 ms |
| DeepGaze IIE | 2 GB | 25 ms |
| CLIP (per-region) | 2 GB | 10 ms/region |
| Low-level features | — | 50 ms |

**Total**: ~200 ms/image on V100, ~8 GB peak memory

**Throughput**: 5 images/second sustained

---

## 10. Integration Architecture

```
                    ┌─────────────────────────────────────────────┐
                    │              Input Image                     │
                    └─────────────────────────────────────────────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    ▼                   ▼                   ▼
            ┌───────────────┐   ┌───────────────┐   ┌───────────────┐
            │  SegFormer-B5 │   │ Depth Any. V2 │   │  DeepGaze IIE │
            └───────────────┘   └───────────────┘   └───────────────┘
                    │                   │                   │
                    ▼                   ▼                   ▼
            ┌───────────────┐   ┌───────────────┐   ┌───────────────┐
            │ Region Masks  │   │  Depth Map    │   │ Saliency Map  │
            └───────────────┘   └───────────────┘   └───────────────┘
                    │                   │                   │
                    └───────────────────┼───────────────────┘
                                        │
                                        ▼
                    ┌─────────────────────────────────────────────┐
                    │           Per-Region Pooling                 │
                    └─────────────────────────────────────────────┘
                                        │
                                        ▼
                    ┌─────────────────────────────────────────────┐
                    │         LocalizedImageTags JSON              │
                    └─────────────────────────────────────────────┘
```

---

## 11. License Summary

| Model | License | Commercial Use |
|-------|---------|----------------|
| SegFormer | Apache 2.0 | ✓ Yes |
| Depth Anything V2 | Apache 2.0 | ✓ Yes |
| DeepGaze IIE | GPL-3.0 | ⚠ Copyleft |
| SAM-ResNet | MIT | ✓ Yes |
| CLIP | MIT | ✓ Yes |

---

## References

Cheng, B., et al. (2022). Masked-attention mask transformer. *CVPR*. [~1,500 citations]

Kümmerer, M., et al. (2017). DeepGaze II. *arXiv*. [~500 citations]

Xie, E., et al. (2021). SegFormer. *NeurIPS*. [~2,500 citations]

Yang, L., et al. (2024). Depth Anything V2. *arXiv*. [~200 citations]

---

*End of Model Selection Matrix v0.1.0*
