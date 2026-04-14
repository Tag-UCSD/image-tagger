# Tag Scope Classification for Neuroarchitecture Image Tagger

**Version**: 0.1.0  
**Date**: 2024-12-21  
**Status**: Draft (pending full TagRegistry v0.2.8 review)  
**Parent**: 01_Core_Specification.md

---

## 1. Purpose

This document classifies each attribute in the TagRegistry by its appropriate **spatial scope**, determining which attributes:
- MUST be localized (ecologically invalid otherwise)
- BENEFIT from localization but can fallback to global
- Are genuinely GLOBAL (no spatial structure)
- Are RELATIONAL (defined between region pairs)

---

## 2. Scope Definitions

| Scope Code | Name | Description | Storage Pattern |
|------------|------|-------------|-----------------|
| `G` | Global | Single value per image, no spatial structure | `global_attributes` |
| `R` | Per-Region | Value per semantic region | `semantic_regions[].attributes` |
| `D` | Dense Map | Continuous spatial representation | `dense_maps[]` |
| `X` | Relational | Defined between region pairs | `contrast_metrics[]` |
| `H` | Hybrid | Multiple scopes (e.g., dense + region + global) | Multiple locations |

**Priority Levels:**
- **P1**: Must localize - attribute is meaningless or misleading without spatial structure
- **P2**: Should localize - significant information loss without spatial structure
- **P3**: May localize - modest benefit, can defer
- **P4**: Global-only - no benefit from localization

---

## 3. Summary Statistics

### By Priority Level

| Priority | Count | Percentage | Description |
|----------|-------|------------|-------------|
| P1 (Must localize) | 67 | 52% | Ecologically invalid without localization |
| P2 (Should localize) | 42 | 33% | Significant information loss |
| P3 (May localize) | 12 | 9% | Modest benefit |
| P4 (Global-only) | 8 | 6% | No benefit from localization |

### By Scope

| Scope | Count | Percentage |
|-------|-------|------------|
| Per-Region (R) | 58 | 45% |
| Hybrid (H) | 24 | 19% |
| Dense Map (D) | 15 | 12% |
| Relational (X) | 18 | 14% |
| Global (G) | 14 | 11% |

### Branch Heat Map

| Branch | P1 | P2 | P3 | P4 | Total | Localization Need |
|--------|----|----|----|----|-------|-------------------|
| A - Luminous | 7 | 4 | 0 | 1 | 12 | HIGH |
| B - Thermal | 0 | 0 | 1 | 1 | 2 | LOW |
| C - Acoustic | 0 | 2 | 1 | 0 | 3 | MEDIUM |
| D - Spatial | 6 | 4 | 2 | 6 | 18 | MIXED |
| E - Complexity | 10 | 4 | 0 | 0 | 14 | CRITICAL |
| F - Color | 7 | 4 | 1 | 0 | 12 | HIGH |
| G - Material | 5 | 4 | 2 | 0 | 11 | HIGH |
| H - Biophilic | 12 | 3 | 1 | 0 | 16 | CRITICAL |
| I - Social | 8 | 3 | 1 | 1 | 13 | HIGH |
| J - Cognitive | 5 | 4 | 1 | 0 | 10 | HIGH |
| K - Affective | 7 | 4 | 0 | 0 | 11 | HIGH |
| L - Temporal | 0 | 0 | 3 | 2 | 5 | LOW |

---

## 4. Classification by Taxonomy Branch

### Branch E: Visual Complexity (CRITICAL)

| Code | Attribute | Scope | Priority | Rationale |
|------|-----------|-------|----------|-----------|
| E.1.1 | Fractal dimension | H (D+R+G) | P1 | **Paradigm case**: dense map shows complexity gradients; per-region enables ceiling-floor comparison |
| E.2.1 | Edge density | H (D+R+G) | P1 | Same rationale as fractal D |
| E.3.1 | Contour entropy | R | P1 | Coburn's measure; per-surface contour statistics |
| E.4.1 | Texture regularity | R | P1 | Varies by surface (patterned floor vs. plain wall) |
| E.6.1 | Information density | D + R | P1 | Spatial distribution of visual information |
| E.7.1 | Coherence | R + X | P1 | Per-region + relational (do regions "fit" together?) |

### Branch H: Biophilic Elements (CRITICAL)

| Code | Attribute | Scope | Priority | Rationale |
|------|-----------|-------|----------|-----------|
| H.1.1 | Plant presence | R | P1 | Location of plants matters (corner vs. focal) |
| H.2.1 | Natural material ratio | R + G | P1 | Per-surface + overall |
| H.3.1 | Nature view presence | R (window) | P1 | Per-window view content |
| H.3.2 | Nature view quality | R | P1 | Sky, vegetation, water per view |
| H.5.1 | Natural light presence | R | P1 | Which regions receive daylight |

### Branch D: Spatial Configuration (MIXED)

| Code | Attribute | Scope | Priority | Rationale |
|------|-----------|-------|----------|-----------|
| D.1.1 | Room height | G | P4 | Single value |
| D.2.1 | Height:width ratio | G | P4 | Derived from globals |
| D.4.1 | Prospect | R + X | P1 | **Critical**: per-window/opening view depth |
| D.4.2 | Refuge | R | P1 | **Critical**: per-corner/alcove enclosure |
| D.4.3 | Mystery | R | P1 | Hildebrand's extension: partial views |

### Branch K: Affective Properties

| Code | Attribute | Scope | Priority | Rationale |
|------|-----------|-------|----------|-----------|
| K.1.1 | Valence | G + R | P1 | Overall affect + per-region variation |
| K.1.2 | Arousal | G + R | P1 | Overall + per-region |
| K.2.1 | Coziness | R | P1 | Per-zone (reading nook vs. grand hall) |
| K.4.1 | Safety perception | R | P1 | Per-zone safety/threat |
| K.5.1 | Awe potential | R | P1 | Per-zone awe-inducing elements |

---

## 5. Critical Path Attributes (P1)

These 67 attributes **must** be implemented with localization from the start:

1. **Visual Complexity (E)**: fractal_dimension, edge_density, contour_entropy, texture_regularity, information_density, visual_clutter, coherence
2. **Biophilic (H)**: All plant, natural material, nature view, and natural light attributes
3. **Prospect-Refuge (D.4)**: prospect, refuge, mystery, enticement
4. **Affective (K)**: valence, arousal, dominance (per-region), coziness, safety, awe
5. **Color (F)**: All per-region color attributes, plus relational harmony/contrast
6. **Social (I)**: gathering space, privacy, interaction potential

---

## 6. Implementation Implications

### Architecture Requirements

1. **Semantic Segmentation**: Required for all per-region attributes (95% of P1-P2)
2. **Dense Maps**: Required for 15 attributes (complexity gradients, depth, saliency)
3. **Relational Computation**: Required for 18 attributes (color harmony, contrast metrics)
4. **Material Segmentation**: Required for material-specific attributes (15 attributes)

### Model Dependencies

| Capability | Required For | Candidate Models |
|------------|--------------|------------------|
| Semantic segmentation | All per-region attributes | SegFormer, OneFormer |
| Material segmentation | Branch G, H.2 | MINC, OpenSurfaces |
| Depth estimation | D.4 (prospect), spatial | Depth Anything V2 |
| Saliency | J.1, attention | DeepGaze II |
| Affect | Branch K | EMOTIC |

---

## 7. Prioritized Implementation Order

### Phase 1: Foundation (Weeks 1-4)
1. Semantic segmentation
2. Depth estimation
3. Basic color extraction per-region

### Phase 2: Complexity (Weeks 5-8)
4. Fractal dimension (dense + region + global)
5. Edge density
6. Contour entropy
7. Texture analysis

### Phase 3: Biophilic & Material (Weeks 9-12)
8. Material segmentation
9. Naturalness computation
10. Plant detection
11. View analysis

### Phase 4: Affect & Social (Weeks 13-16)
12. Lighting estimation
13. Affective inference
14. Social affordance detection

### Phase 5: Relational & Integration (Weeks 17-20)
15. Contrast metrics
16. Harmony computation
17. Full pipeline validation

---

*End of Tag Scope Classification v0.1.0*
