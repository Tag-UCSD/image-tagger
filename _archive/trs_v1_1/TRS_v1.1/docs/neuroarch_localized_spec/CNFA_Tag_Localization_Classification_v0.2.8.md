# CNFA Tag Registry v0.2.8 — Localization Priority Classification

**Registry Version**: 0.2.8  
**Classification Date**: 2024-12-21  
**Total Tags**: 424  
**Source**: `cnfa_tag_registry_canonical_v0_2_8.yaml`

---

## Executive Summary

| Priority | Count | Percentage | Description |
|----------|-------|------------|-------------|
| **P1** | 154 | 36.3% | Must localize — ecologically invalid without spatial context |
| **P2** | 149 | 35.1% | Should localize — significant information loss from aggregation |
| **P3** | 121 | 28.5% | May localize — modest benefit, global acceptable |
| **P4** | 0 | 0.0% | Global only — localization not applicable |

**Key Finding**: **71.5% of tags** (303 of 424) require or strongly benefit from localization. The scalar-per-image architecture fundamentally cannot capture this spatial structure.

---

## Priority Definitions

### P1: Must Localize (154 tags, 36.3%)
**Ecological validity requires localization.** These attributes are meaningless or misleading when averaged across the entire image.

Characteristics:
- Surface-bound (wall material, ceiling treatment, floor texture)
- Component-specific (fixtures, hardware, architectural elements)
- Light distribution (illuminance varies by location)
- Spatial affordances (prospect-refuge, enclosure, landmarks)

### P2: Should Localize (149 tags, 35.1%)
**Significant information loss from aggregation.** The global mean obscures important spatial variation.

Characteristics:
- Style detection (can vary by zone within one image)
- Complexity metrics (clutter concentrated in certain areas)
- Color attributes (accent walls, focal surfaces differ)
- Biophilic elements (plants, natural materials localized)

### P3: May Localize (121 tags, 28.5%)
**Modest benefit from localization.** Global measurement acceptable but per-region adds insight.

Characteristics:
- Room function (inherently whole-room classification)
- Spatial configuration (volume, overall height)
- Social arrangement (gathering patterns)
- Control/personalization (user agency)

### P4: Global Only (0 tags, 0.0%)
No tags in this registry are purely global. This confirms the architecture's bias toward attributes that inherently vary spatially.

---

## Classification by Domain

### Arch (20 tags) — 100% P1
All architectural pattern tags are inherently location-specific.

| Priority | Count | Examples |
|----------|-------|----------|
| P1 | 20 | Wall treatments, ceiling types, window configurations |

### Component (19 tags) — 100% P1
Component attributes are bound to specific building elements.

| Priority | Count | Examples |
|----------|-------|----------|
| P1 | 19 | Fixtures, hardware, fittings, built-in elements |

### Materials (14 tags) — 100% P1
Material attributes vary fundamentally by surface.

| Priority | Count | Examples |
|----------|-------|----------|
| P1 | 14 | Surface materials, finishes, substrates |

### Style (11 tags) — 100% P2
Style can vary by zone within a single space.

| Priority | Count | Examples |
|----------|-------|----------|
| P2 | 11 | Mid-century, industrial, scandinavian, minimalist |

### Color (14 tags) — 93% P2
Color attributes benefit strongly from per-surface analysis.

| Priority | Count | Examples |
|----------|-------|----------|
| P1 | 1 | — |
| P2 | 13 | Palette, harmony, saturation, hue dominance |

### H. Visual Complexity & Order (22 tags) — 82% P2
Complexity metrics vary spatially but pattern can be detected.

| Priority | Count | Examples |
|----------|-------|----------|
| P1 | 4 | Pattern, texture detail |
| P2 | 18 | Fractal D, entropy, clutter, rhythm |

### I. Biophilic Elements & Views (20 tags) — 100% P1+P2
Biophilic elements are inherently localized (plants, natural materials, views).

| Priority | Count | Examples |
|----------|-------|----------|
| P1 | 9 | Natural materials, greenery placement |
| P2 | 11 | Biophilic ratio, nature connection |

### A. Luminous Environment (41 tags) — 54% P1+P2
Light distribution varies by location but some metrics are scene-level.

| Priority | Count | Examples |
|----------|-------|----------|
| P1 | 15 | Illuminance distribution, shadow patterns, glare zones |
| P2 | 7 | Color temperature, warmth, brightness |
| P3 | 19 | Overall daylight factor, ambient level |

### G. Spatial Configuration & Geometry (39 tags) — 74% P1+P2
Spatial metrics have both local and global components.

| Priority | Count | Examples |
|----------|-------|----------|
| P1 | 18 | Enclosure, prospect-refuge, anchors |
| P2 | 11 | Symmetry, balance, proportions |
| P3 | 10 | Volume, overall height, spaciousness |

### Cnfa (48 tags) — 100% P1+P2
All computed CNfA metrics benefit from or require localization.

| Priority | Count | Examples |
|----------|-------|----------|
| P1 | 12 | Haptic texture, surface fluency, edge clarity |
| P2 | 36 | Complexity indices, biophilic ratios, aesthetic metrics |

### Lighting (12 tags) — 100% P1+P2
Light attributes vary by zone.

| Priority | Count | Examples |
|----------|-------|----------|
| P1 | 6 | Luminance at surfaces, shadow quality |
| P2 | 6 | Warmth, layering, contrast |

### J. Social-Spatial Factors (18 tags) — 28% P1+P2
Social attributes are often scene-level.

| Priority | Count | Examples |
|----------|-------|----------|
| P1 | 1 | Focal gathering point |
| P2 | 4 | Seating arrangement density |
| P3 | 13 | Social affordances, gathering capacity |

### K. Control & Personalization (16 tags) — 38% P1+P2
Control attributes are mostly scene-level but some are localized.

| Priority | Count | Examples |
|----------|-------|----------|
| P1 | 4 | Interactive surfaces, control points |
| P2 | 2 | Personalization zones |
| P3 | 10 | Overall user agency, flexibility |

### Spatial (11 tags) — 18% P1+P2
Spatial metrics are mostly global scene descriptions.

| Priority | Count | Examples |
|----------|-------|----------|
| P1 | 1 | Landmark presence |
| P2 | 1 | Wayfinding clarity |
| P3 | 9 | Room function, openness, volume |

### Geometry (11 tags) — 45% P1+P2
Geometric attributes have both local and global aspects.

| Priority | Count | Examples |
|----------|-------|----------|
| P1 | 3 | Surface geometry, edge details |
| P2 | 2 | Proportional harmony |
| P3 | 6 | Overall form, height ratios |

---

## Classification by Status

| Status | P1 | P2 | P3 | P4 | Total | P1+P2 % |
|--------|----|----|----|----|-------|---------|
| **active** | 84 | 82 | 82 | 0 | 248 | 66.9% |
| **existing** | 67 | 47 | 32 | 0 | 146 | 78.1% |
| **proposed_delta** | 3 | 20 | 7 | 0 | 30 | 76.7% |

The "existing" tags (already implemented) have the highest P1+P2 ratio, suggesting the system evolved toward spatially-meaningful attributes.

---

## Implementation Roadmap

### Phase 1: P1 Infrastructure (154 tags)
**Must localize — ecologically invalid without spatial context**

Required capabilities:
- Semantic segmentation (shell surfaces: ceiling, floor, walls, windows, doors)
- Wall separation (distinguish back wall from flanking walls)
- Component detection (fixtures, furniture, architectural elements)
- Per-region attribute computation

Key domains:
- Arch (20 tags)
- Component (19 tags)
- Materials (14 tags)
- Light distribution (15 tags from Luminous)
- Spatial affordances (18 tags from Spatial Config)

### Phase 2: P2 Enhancement (149 tags)
**Should localize — significant information loss from aggregation**

Additional capabilities:
- Per-zone style detection
- Per-surface color analysis
- Localized complexity metrics
- Biophilic element mapping

Key domains:
- Style (11 tags)
- Color (14 tags)
- Visual Complexity (22 tags)
- Biophilic (20 tags)
- Cnfa computed metrics (48 tags)

### Phase 3: P3 Optimization (121 tags)
**May localize — modest benefit, global acceptable**

Optional enhancements:
- Room function with zone awareness
- Path-based spatial metrics
- Social arrangement mapping
- Control point detection

Key domains:
- Spatial (11 tags)
- Geometry (11 tags)
- Social-Spatial (18 tags)
- Control/Personalization (16 tags)

---

## Comparison with Prior Estimates

| Analysis | P1 | P2 | P3 | P4 | Total | P1+P2 % |
|----------|----|----|----|----|-------|---------|
| Doc 02 (taxonomy slice) | 67 | 42 | 15 | 5 | 129 | 84.5% |
| features_canonical.jsonl | 48 | 36 | 26 | 2 | 112 | 75.0% |
| **Full Registry v0.2.8** | **154** | **149** | **121** | **0** | **424** | **71.5%** |

The consistent pattern across all analyses: **approximately 70-85% of attributes require or strongly benefit from localization.**

---

## Technical Notes

### Region Support Flag
The registry includes a `region_support` field in extractability. Currently only 4 tags have this set to `true`, but our analysis shows 154 tags **require** it and 149 more **benefit** from it.

### Extractability from 2D
- 239 tags (56%): `from_2d: yes`
- 173 tags (41%): `from_2d: partial`
- 12 tags (3%): `from_2d: no`

The high rate of 2D extractability confirms that most localization can be achieved from standard images without requiring 3D scans.

### Integration with Localized Pipeline
The `Neuroarch_Localized_Integration_v0.1.0` package provides:
- SegFormer semantic segmentation → shell masks
- Wall separation algorithm → distinct wall regions
- Per-region attribute pooling → localized metrics
- Contrast computation → ceiling-floor, focal-flanking differences

This infrastructure directly addresses the P1 requirements and enables P2 enhancements.

---

*End of Classification — CNFA Tag Registry v0.2.8*
