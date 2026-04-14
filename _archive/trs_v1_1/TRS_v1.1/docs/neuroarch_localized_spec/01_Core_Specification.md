# Neuroarchitecture Localized Attribute Architecture Specification

**Version**: 0.1.0  
**Date**: 2024-12-21  
**Status**: Draft  
**Author**: David Kirsh (UCSD Cognitive Science) with Claude (Anthropic)  
**Related Systems**: Image Tagger v3.4.74, TagRegistry v0.2.8, Article Finder v2.2.0, Article Eater

---

## Document Purpose

This specification defines the **localized attribute architecture** for the Neuroarchitecture Image Tagger system. It supersedes the prior scalar-per-image approach, which stored global values (e.g., `{"fractal.D": 1.47}`) without spatial information.

The core insight motivating this redesign: **humans perceive architectural environments locally, not globally**. Storing only aggregate statistics discards the spatial structure that matters for understanding how built environments affect cognition.

---

## Table of Contents

1. [Project Constitution](#1-project-constitution)
2. [Semantic Region Vocabulary](#2-semantic-region-vocabulary)
3. [Tag Scope Classification](#3-tag-scope-classification)
4. [Localized Attribute Schema](#4-localized-attribute-schema)
5. [Dense Map Specification](#5-dense-map-specification)
6. [Contrast and Relational Metrics](#6-contrast-and-relational-metrics)
7. [Storage Architecture](#7-storage-architecture)
8. [Provenance and Versioning](#8-provenance-and-versioning)
9. [Query Interface](#9-query-interface)
10. [Integration Contracts](#10-integration-contracts)
11. [References](#11-references)

---

## 1. Project Constitution

### 1.1 Purpose

The Neuroarchitecture Image Tagger extracts **computable visual features** from interior space images to support research on how architectural and environmental factors affect human cognition. This system:

1. Operationalizes psychological constructs (complexity, prospect-refuge, coherence) as measurable image features
2. Stores features with spatial structure (per-region, dense maps) not just global scalars
3. Enables pattern discovery across image collections (e.g., "find interiors where ceiling complexity exceeds floor complexity by > 0.4")
4. Integrates with the broader research infrastructure (Article Finder, Article Eater, Bayesian Network repository)

### 1.2 Non-Negotiables

Following the governance patterns established in Article Finder:

1. **No deletions.** If schema versions change, archive prior versions. Never delete data.

2. **Monotonic safety.** Releases must not lose attributes or reduce coverage. New versions extend; they do not subtract.

3. **Explainability.** Every computed value must record: which model/algorithm produced it, which version, what parameters, when computed. Auditability is required.

4. **Ecological validity.** Operationalizations must have published empirical support linking the computed feature to human perceptual or cognitive outcomes. Ad hoc features without theoretical grounding are prohibited.

5. **Localization-first.** New attributes default to per-region or dense-map storage unless there is principled justification for global-only computation.

6. **Schema contracts.** Changes to the attribute schema require version bumps and migration documentation. Downstream systems (Bayesian Network, query interfaces) depend on schema stability.

### 1.3 What Counts as "Done"

- Semantic segmentation produces labeled regions for all primary architectural surfaces
- Per-region attributes are computed for all implemented tags
- Dense maps are generated for attributes flagged as requiring continuous spatial information
- Contrast metrics are computed for all defined region pairs
- Provenance metadata accompanies every computed value
- Query interface supports region-level and cross-region pattern matching

---

## 2. Semantic Region Vocabulary

### 2.1 Design Rationale

The vocabulary defines **what architectural elements** we recognize and compute attributes for. This is foundational—the entire localized architecture references these labels.

**Design decisions** (per consultation 2024-12-21):
- Primary focus is the **architectural shell** (walls, ceiling, floor, openings)
- Individual walls are distinguished (for asymmetric complexity analysis)
- Furniture/fixtures receive identifiers but are secondary to shell analysis
- Outdoor/transitional regions are included (necessary for prospect-refuge judgments)
- Attributes can be computed per-element OR per-material-region (both supported)

### 2.2 Vocabulary Hierarchy

#### Level 0: Image-Global
Reserved for attributes that genuinely have no spatial structure.

| Code | Label | Description |
|------|-------|-------------|
| `global` | Whole Image | Aggregate statistics, overall room dimensions |

#### Level 1: Primary Architectural Surfaces (Shell)
The "big six" that define spatial enclosure. These are the primary focus.

| Code | Label | Description | Sub-segmentation |
|------|-------|-------------|------------------|
| `ceiling` | Ceiling | Upper horizontal enclosure | May include `ceiling.coffer`, `ceiling.beam` |
| `floor` | Floor | Lower horizontal enclosure | May include `floor.level_change`, `floor.step` |
| `wall.N` | Wall (North) | Vertical enclosure, north-facing | Material discontinuities create sub-regions |
| `wall.E` | Wall (East) | Vertical enclosure, east-facing | |
| `wall.S` | Wall (South) | Vertical enclosure, south-facing | |
| `wall.W` | Wall (West) | Vertical enclosure, west-facing | |
| `wall.focal` | Focal Wall | Perceptually dominant wall (if identifiable) | |
| `window` | Window | Glazed opening, including frame | `window.glazing`, `window.frame` |
| `door` | Door | Passage with closure, including frame | `door.panel`, `door.frame` |
| `opening` | Opening | Archway, passage without door | |

**Note on wall identification**: In images where compass orientation is unknown, walls may be labeled by position relative to viewpoint (`wall.left`, `wall.right`, `wall.back`) or by perceptual salience (`wall.focal`, `wall.flanking`). The schema supports both conventions.

#### Level 2: Architectural Features
Elements attached to or modifying primary surfaces.

| Code | Label | Description | Parent Surface |
|------|-------|-------------|----------------|
| `column` | Column/Pillar | Vertical structural element | — |
| `beam` | Beam | Horizontal structural element | ceiling |
| `molding` | Molding/Cornice | Decorative trim at ceiling junction | ceiling, wall |
| `baseboard` | Baseboard | Trim at floor-wall junction | wall, floor |
| `chair_rail` | Chair Rail | Horizontal wall trim | wall |
| `wainscoting` | Wainscoting | Lower wall paneling | wall |
| `stairs` | Stairs | Vertical circulation | floor |
| `railing` | Railing/Balustrade | Safety barrier | stairs, balcony |
| `fireplace` | Fireplace | Hearth and surround | wall |
| `niche` | Niche/Alcove | Recessed wall area | wall |
| `bay_window` | Bay Window | Projecting window area | wall, window |
| `skylight` | Skylight | Ceiling glazing | ceiling |
| `clerestory` | Clerestory | High window band | wall |

#### Level 3: Fixtures and Furniture
Moveable or semi-permanent elements. Included for completeness but secondary to shell analysis.

| Code | Label | Description |
|------|-------|-------------|
| `chandelier` | Chandelier | Suspended decorative lighting |
| `pendant` | Pendant Light | Suspended task/ambient lighting |
| `sconce` | Wall Sconce | Wall-mounted lighting |
| `recessed_light` | Recessed Light | Ceiling-embedded lighting |
| `lamp` | Lamp | Portable lighting fixture |
| `chair` | Chair | Seating, single |
| `sofa` | Sofa/Couch | Seating, multiple |
| `table` | Table | Horizontal work/gathering surface |
| `desk` | Desk | Work surface with storage |
| `bed` | Bed | Sleep furniture |
| `cabinet` | Cabinet/Closet | Storage, enclosed |
| `bookshelf` | Bookshelf | Storage, open |
| `plant` | Plant | Biophilic element, living |
| `artwork` | Artwork | Wall-mounted decorative element |
| `rug` | Rug/Carpet | Floor covering, partial |
| `curtain` | Curtain/Drape | Window covering, soft |

#### Level 4: Transitional and Exterior
Regions visible through openings. Essential for prospect-refuge analysis.

| Code | Label | Description |
|------|-------|-------------|
| `view.exterior` | Exterior View | Outdoor scene visible through window |
| `view.adjacent` | Adjacent Room | Interior space visible through opening |
| `balcony` | Balcony/Terrace | Semi-outdoor transitional space |
| `courtyard` | Courtyard | Enclosed exterior space |
| `threshold` | Threshold | Boundary zone at door/opening |

#### Level 5: Materials (Cross-Cutting)
Material labels can apply to any region. These enable per-material attribute computation.

| Code | Label | Description |
|------|-------|-------------|
| `mat.wood` | Wood | Natural wood grain |
| `mat.stone` | Stone | Natural stone (marble, granite, slate) |
| `mat.brick` | Brick | Fired clay units |
| `mat.concrete` | Concrete | Poured or precast cement |
| `mat.metal` | Metal | Ferrous and non-ferrous |
| `mat.glass` | Glass | Transparent/translucent glazing |
| `mat.fabric` | Fabric | Textile materials |
| `mat.leather` | Leather | Animal hide |
| `mat.plaster` | Plaster | Applied wall/ceiling finish |
| `mat.tile` | Tile | Ceramic/porcelain units |
| `mat.carpet` | Carpet | Floor textile, wall-to-wall |
| `mat.paint` | Paint | Applied coating |
| `mat.wallpaper` | Wallpaper | Applied wall covering |

### 2.3 Region Relationships

Regions exist in hierarchical and spatial relationships:

**Containment** (`contains`): A window is contained within a wall. Schema supports:
```json
{
  "region_id": "wall.N",
  "contains": ["window.1", "door.1"]
}
```

**Adjacency** (`adjacent_to`): Ceiling is adjacent to walls. Enables junction analysis:
```json
{
  "region_id": "ceiling",
  "adjacent_to": ["wall.N", "wall.E", "wall.S", "wall.W", "molding"]
}
```

**Material overlay**: A region can have material sub-regions:
```json
{
  "region_id": "floor",
  "material_regions": [
    {"material": "mat.wood", "area_fraction": 0.7},
    {"material": "mat.tile", "area_fraction": 0.3}
  ]
}
```

---

## 3. Tag Scope Classification

### 3.1 Classification Rationale

Not all 424 tags in TagRegistry v0.2.8 benefit equally from localization. This section classifies each attribute by its appropriate spatial scope.

**Scope Categories**:

| Scope | Description | Example |
|-------|-------------|---------|
| `global` | Genuinely image-wide, no spatial structure | Room volume, overall aspect ratio |
| `per_region` | Meaningful at region level, not globally | Ceiling fractal D, wall color |
| `dense_map` | Requires continuous spatial representation | Edge density map, depth map |
| `relational` | Defined between region pairs | Ceiling-floor complexity contrast |
| `hybrid` | Computed at multiple scopes | Fractal D: dense + per-region + global |

See `02_Tag_Scope_Classification.md` for complete attribute classification.

---

## 4. Localized Attribute Schema

### 4.1 Top-Level Structure

```typescript
interface LocalizedImageTags {
  // Metadata
  image_id: string;                    // Unique identifier
  image_source: ImageSource;           // Provenance
  schema_version: string;              // "0.1.0"
  computed_at: string;                 // ISO 8601 timestamp
  
  // Global attributes (scope = global)
  global_attributes: GlobalAttributes;
  
  // Semantic segmentation output
  semantic_regions: SemanticRegion[];
  
  // Dense attribute maps
  dense_maps: DenseMapReference[];
  
  // Cross-region relationships
  region_relationships: RegionRelationship[];
  
  // Contrast and relational metrics
  contrast_metrics: ContrastMetric[];
  
  // Computation provenance
  pipeline_provenance: PipelineProvenance;
}
```

### 4.2 Semantic Region

```typescript
interface SemanticRegion {
  region_id: string;                   // e.g., "wall.N", "ceiling"
  region_label: string;                // Human-readable label
  vocabulary_code: string;             // Reference to Section 2 vocabulary
  
  // Segmentation geometry
  mask_reference: MaskReference;       // Pointer to binary mask
  bounding_box: BoundingBox;           // [x, y, width, height]
  area_pixels: number;                 // Pixel count
  area_fraction: number;               // Fraction of image
  centroid: [number, number];          // [x, y] center
  
  // Hierarchical relationships
  parent_region?: string;              // Containing region
  child_regions?: string[];            // Contained regions
  adjacent_regions?: string[];         // Spatially adjacent
  
  // Material composition (if segmented)
  material_composition?: MaterialComposition[];
  
  // Per-region attributes
  attributes: RegionAttributes;
}

interface AttributeValue {
  value: number | number[] | string;
  confidence?: number;                 // 0-1, model confidence
  provenance: AttributeProvenance;
}

interface AttributeProvenance {
  model_id: string;                    // e.g., "kardan_edge_v1"
  model_version: string;
  computation_date: string;            // ISO 8601
  parameters?: Record<string, any>;    // Model-specific params
  source_reference?: string;           // DOI or citation key
}
```

See `contracts/localized_image_tags.schema.json` for complete JSON Schema.

---

## 5. Dense Map Specification

### 5.1 When to Use Dense Maps

Dense maps store per-pixel or per-patch attribute values. Use when:

1. **Spatial gradient matters**: Edge density varies across the image in ways that per-region averages would obscure
2. **Region boundaries are uncertain**: Some attributes (depth, lighting) vary continuously
3. **Pattern discovery requires spatial structure**: Finding images with specific complexity gradients

### 5.2 Standard Dense Maps

| Attribute | Resolution | Window | Format | Notes |
|-----------|------------|--------|--------|-------|
| `depth` | Native | — | float32 | Depth Anything V2 output |
| `fractal_dimension` | 1/8 native | 64×64 | float16 | Sliding window box-counting |
| `edge_density` | 1/4 native | 32×32 | float16 | Canny edge ratio per window |
| `saliency` | 1/4 native | — | float16 | DeepGaze II or SAM-ResNet |
| `semantic_index` | 1/4 native | — | uint8 | ADE20K class indices |
| `material_index` | 1/4 native | — | uint8 | MINC class indices |

---

## 6. Contrast and Relational Metrics

### 6.1 Rationale

Many neuroarchitectural hypotheses concern **relationships between regions**, not individual regions:

- "Ornate ceilings with plain walls create visual hierarchy"
- "Complexity decreases from focal wall to flanking walls"
- "High prospect (window views) combined with high refuge (enclosed alcoves)"

### 6.2 Standard Contrast Metrics

| Metric ID | Regions | Attribute | Formula | Theoretical Basis |
|-----------|---------|-----------|---------|-------------------|
| `ceiling_floor_complexity_diff` | ceiling, floor | fractal_D | A - B | Visual hierarchy |
| `focal_flanking_complexity_ratio` | wall.focal, wall.flanking | fractal_D | A / mean(B) | Attention direction |
| `window_wall_luminance_ratio` | window, wall.* | luminance | A / B | Daylight contrast |
| `prospect_refuge_ratio` | view.exterior, niche | area | A / B | Appleton (1975) |
| `color_harmony_adjacent` | wall.N, wall.E | hue | angular_diff | Itten color theory |

---

## 7. Storage Architecture

### 7.1 Hybrid Storage Model

| Data Type | Storage | Format | Rationale |
|-----------|---------|--------|-----------|
| Structured metadata | SQLite | Relational tables | Query flexibility |
| Per-region attributes | SQLite | JSON columns | Schema flexibility |
| Dense maps | Filesystem | Binary + JSON meta | Size, lazy loading |
| Masks | Filesystem | RLE or PNG | Size, interoperability |

### 7.2 SQLite Schema

```sql
CREATE TABLE images (
    image_id TEXT PRIMARY KEY,
    source_path TEXT,
    width INTEGER,
    height INTEGER,
    schema_version TEXT,
    computed_at TEXT,
    pipeline_version TEXT
);

CREATE TABLE regions (
    region_id TEXT,
    image_id TEXT,
    region_label TEXT,
    vocabulary_code TEXT,
    bbox_x INTEGER,
    bbox_y INTEGER,
    bbox_w INTEGER,
    bbox_h INTEGER,
    area_pixels INTEGER,
    area_fraction REAL,
    mask_path TEXT,
    attributes_json TEXT,
    PRIMARY KEY (image_id, region_id),
    FOREIGN KEY (image_id) REFERENCES images(image_id)
);

CREATE TABLE dense_maps (
    image_id TEXT,
    attribute_id TEXT,
    resolution_w INTEGER,
    resolution_h INTEGER,
    format TEXT,
    storage_path TEXT,
    value_min REAL,
    value_max REAL,
    provenance_json TEXT,
    PRIMARY KEY (image_id, attribute_id)
);

CREATE TABLE contrast_metrics (
    image_id TEXT,
    metric_id TEXT,
    region_a TEXT,
    region_b TEXT,
    attribute_id TEXT,
    value REAL,
    provenance_json TEXT,
    PRIMARY KEY (image_id, metric_id)
);
```

---

## 8. Provenance and Versioning

### 8.1 Provenance Requirements

Every computed value must record:

1. **What** model/algorithm produced it
2. **Which version** of that model
3. **When** it was computed
4. **What parameters** were used
5. **What source** (literature) justifies the operationalization

### 8.2 Schema Versioning

Schema versions follow semantic versioning:
- **Major**: Breaking changes to core structure
- **Minor**: New attributes or regions added (backward compatible)
- **Patch**: Bug fixes, documentation

---

## 9. Query Interface

### 9.1 Query Examples

**SQL - Find images with high ceiling complexity:**
```sql
SELECT i.image_id, json_extract(r.attributes_json, '$.fractal_dimension.value') as fd
FROM images i
JOIN regions r ON i.image_id = r.image_id
WHERE r.vocabulary_code = 'ceiling'
  AND json_extract(r.attributes_json, '$.fractal_dimension.value') > 1.5
ORDER BY fd DESC;
```

**SQL - Find images with high complexity contrast:**
```sql
SELECT image_id, value as contrast
FROM contrast_metrics
WHERE metric_id = 'ceiling_floor_complexity_diff'
  AND value > 0.4
ORDER BY value DESC;
```

---

## 10. Integration Contracts

### 10.1 Image Tagger ↔ Bayesian Network

The Bayesian Network repository consumes image tags to model relationships between environmental features and cognitive outcomes.

**Contract**:
- Image Tagger produces `LocalizedImageTags` conforming to this specification
- Bayesian Network can query by region, attribute, or contrast metric
- Schema version compatibility is checked at integration time

### 10.2 Image Tagger ↔ Article Eater

Article Eater extracts claims about feature-outcome relationships from literature. These claims inform which attributes to implement and how to validate them.

---

## 11. References

Bell, S., Upchurch, P., Snavely, N., & Bala, K. (2015). Material recognition in the wild with the Materials in Context Database. *CVPR*, 3479-3487. [~1,200 citations]

Berman, M. G., et al. (2014). The perception of naturalness correlates with low-level visual features of environmental scenes. *PloS one*, 9(12), e114572. [~200 citations]

Coburn, A., Vartanian, O., & Chatterjee, A. (2017). Buildings, beauty, and the brain: A neuroscience of architectural experience. *Journal of Cognitive Neuroscience*, 29(9), 1521-1531. [~300 citations]

Hildebrand, G. (1999). *Origins of Architectural Pleasure*. University of California Press. [~500 citations]

Kardan, O., et al. (2015). Is the preference of natural versus man-made scenes driven by bottom-up processing of the visual features of nature? *Frontiers in Psychology*, 6, 471. [~250 citations]

Zhou, B., et al. (2017). Scene parsing through ADE20K dataset. *CVPR*, 633-641. [~3,000 citations]

---

*End of Core Specification v0.1.0*
