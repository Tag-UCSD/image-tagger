# Tag Semantics Schema — Disambiguation & Relationships

## Overview

The semantics layer handles ambiguity resolution, tag relationships, and inference rules.
This is critical for ensuring consistent tagging across the Image Tagger, BN, and Article Eater.

---

## Semantics Object Structure

```yaml
semantics:
  # === IDENTITY & ALIASES ===
  aliases: list[str]
    # Synonyms that map to this tag
    # Example: ["warm lighting", "warm lights", "yellowish light"]
  
  preferred_label: str
    # Display name for UI (may differ from canonical_name)
  
  abbreviation: str|null
    # Short code for compact display
    # Example: "CCT" for correlated_color_temperature
  
  # === DISAMBIGUATION ===
  disambiguation:
    context_hints: list[str]
      # Words/phrases that suggest this tag over similar ones
      # Example: ["kelvin", "color temperature"] → lighting.cct vs color.warmth
    
    exclusions: list[str]
      # Context clues that indicate NOT this tag
      # Example: ["paint color", "wall color"] → excludes lighting.cct
    
    requires_cooccurrence: list[str]
      # Tags that must also be present for this to be valid
      # Example: refuge_nook requires some enclosure indicator
    
    confidence_threshold: float
      # Minimum confidence to activate (0.0-1.0)
      # Higher for ambiguous tags to reduce false positives
      # Default: 0.5
    
    priority_over: list[str]
      # When both could apply, this tag wins
      # Example: "high_ceiling" has priority over "open_plan" for height cues
    
    subsumes: list[str]
      # Tags that are automatically true if this is true
      # Example: "double_height_space" subsumes "high_ceiling"
  
  # === RELATIONSHIPS ===
  hierarchy:
    parent: str|null
      # Broader category tag
      # Example: env.lighting.cct_warmth → parent: env.lighting
    
    children: list[str]
      # More specific variants
      # Example: env.lighting → children: [env.lighting.cct_warmth, env.lighting.illuminance]
    
    granularity: enum[coarse, medium, fine]
      # Level of specificity
  
  relations:
    inverse_of: str|null
      # Opposite tag (if one exists)
      # Example: high_ceiling ↔ low_ceiling
    
    related_tags: list[str]
      # Semantically related (not parent/child)
      # Example: "warm_lighting" related to "cozy", "comfort"
    
    often_cooccurs_with: list[str]
      # Statistically frequent co-occurrence
      # Learned from image database
    
    mutually_exclusive_with: list[str]
      # Cannot both be true for same region/image
      # Example: "open_plan" vs "compartmentalized"
    
    implies: list[str]
      # If this tag, then those tags likely
      # Example: "daylighting" implies "window_presence"
    
    implied_by: list[str]
      # Reverse of implies
  
  # === FACTOR MAPPINGS ===
  factor_associations: list[str]
    # Abstract psychological/cognitive factors
    # Example: ["lighting_warmth", "comfort_affect", "coziness"]
  
  factor_direction: dict[str, enum[positive, negative, complex]]
    # How this tag affects each factor
    # Example: {comfort_affect: positive, alertness: negative}
  
  # === SCOPE & APPLICABILITY ===
  scope:
    applies_to: enum[whole_image, region, both]
      # Whether tag applies to full image or can be regional
    
    typical_regions: list[str]
      # For regional tags, common region types
      # Example: ["ceiling", "window_area", "seating_zone"]
    
    room_types: list[str]|null
      # Room types where this tag is most relevant
      # null = all room types
      # Example: ["living_room", "bedroom"] for "cozy"
    
    excluded_room_types: list[str]
      # Room types where tag is typically N/A
      # Example: ["bathroom"] for "double_height_space"
  
  # === MEASUREMENT CONTEXT ===
  measurement:
    unit: str|null
      # Physical unit if applicable
    
    reference_standard: str|null
      # Standard this relates to (WELL, LEED, ASHRAE, etc.)
    
    threshold_values: dict|null
      # Named thresholds
      # Example: {low: 0-200, medium: 200-500, high: 500+} for illuminance
    
    ordinal_anchors: list[str]|null
      # Labels for ordinal values
      # Example: ["very low", "low", "medium", "high", "very high"]
```

---

## Disambiguation Rules Engine

When multiple tags could apply, the following resolution process is used:

### Rule 1: Exclusion Check
If context contains any `exclusion` phrase for a tag, drop that tag.

### Rule 2: Cooccurrence Requirement
If a tag has `requires_cooccurrence`, check those tags are present.

### Rule 3: Mutual Exclusivity
If two mutually exclusive tags both exceed threshold, keep highest confidence.

### Rule 4: Subsumption
If a tag `subsumes` another and both are true, keep only the subsuming tag
(more specific wins).

### Rule 5: Priority Resolution
If two tags compete for same visual cue, check `priority_over` relationship.

### Rule 6: Confidence Threshold
Tags below their `confidence_threshold` are dropped.

---

## Example: Disambiguating "Warmth"

Consider an image with warm-toned lighting and warm-colored walls.

**Candidate tags:**
- `env.lighting.cct_warmth` (lighting color temperature)
- `env.color.palette_warmth` (surface color warmth)
- `pref.affect.cozy` (affective impression)

**Disambiguation process:**

1. `env.lighting.cct_warmth`:
   - context_hints: ["light source", "lamp", "window light"]
   - Check if image has identifiable light sources with warm tones
   
2. `env.color.palette_warmth`:
   - context_hints: ["wall", "floor", "furniture"]
   - Check if surfaces (not light sources) have warm tones
   
3. `pref.affect.cozy`:
   - requires_cooccurrence: suggests warmth + soft furnishings + enclosure
   - Check if multiple cozy indicators present

**Result:** All three could be true simultaneously since they measure different things.
But `cozy` requires convergent evidence while the others are independent measurements.

---

## Handling Inverse/Opposing Tags

For tags with `inverse_of` relationships:

```yaml
env.spatial.ceiling_height_high:
  semantics:
    inverse_of: env.spatial.ceiling_height_low
    mutually_exclusive_with: [env.spatial.ceiling_height_low]

env.spatial.ceiling_height_low:
  semantics:
    inverse_of: env.spatial.ceiling_height_high
    mutually_exclusive_with: [env.spatial.ceiling_height_high]
```

**Resolution:** If both are detected:
1. If one has significantly higher confidence (>0.2 difference), keep that one
2. If similar confidence, mark as `ceiling_height_ambiguous` or output middle value
3. Never output both for same region

---

## Hierarchy Navigation

Tags exist in a hierarchy allowing drill-down and roll-up:

```
env.lighting (domain)
├── env.lighting.intensity (subdomain)
│   ├── env.lighting.illuminance_task
│   ├── env.lighting.illuminance_ambient
│   └── env.lighting.brightness_variance
├── env.lighting.color (subdomain)
│   ├── env.lighting.cct_warmth
│   ├── env.lighting.cri
│   └── env.lighting.saturation
└── env.lighting.distribution (subdomain)
    ├── env.lighting.uniformity
    ├── env.lighting.contrast
    └── env.lighting.glare
```

**Roll-up rules:**
- `env.lighting.intensity` = aggregate of child illuminance tags
- Used when fine-grained extraction not possible

**Drill-down rules:**
- If `env.lighting` detected at coarse level, attempt child extraction
- Populate children with partial confidence if evidence is ambiguous

---

## Scope Handling

### Whole-Image Tags
```yaml
env.spatial.room_type:
  scope:
    applies_to: whole_image
```
→ Only one value per image

### Regional Tags
```yaml
env.lighting.glare_zone:
  scope:
    applies_to: region
    typical_regions: ["window_area", "light_fixture"]
```
→ Multiple regions can have this tag with different values

### Both
```yaml
env.material.wood_presence:
  scope:
    applies_to: both
```
→ Whole-image: binary presence
→ Regional: specific surfaces with wood

---

## Integration with Image Tagger

The Image Tagger uses semantics for:

1. **Pre-filtering**: Skip tags whose `excluded_room_types` match detected room
2. **Disambiguation**: Apply rules when multiple candidates detected
3. **Confidence calibration**: Use `confidence_threshold` to filter weak detections
4. **Relationship inference**: If tag X detected, check `implies` for propagation
5. **Hierarchy filling**: Roll up fine-grained tags to coarse parents

---

## Integration with Bayesian Network

The BN uses semantics for:

1. **Factor mapping**: `factor_associations` → which latent variables affected
2. **Direction encoding**: `factor_direction` → positive/negative edges
3. **Cooccurrence priors**: `often_cooccurs_with` → dependency structure hints
4. **Constraint propagation**: `mutually_exclusive_with` → structural zeros in CPTs

---

## Integration with Article Eater

The AE uses semantics for:

1. **Query expansion**: `aliases` + `context_hints` → richer search queries
2. **Disambiguation in text**: `exclusions` → filter irrelevant papers
3. **Relationship discovery**: Compare paper findings to `implies`/`related_tags`
4. **Factor validation**: Check paper measures against `factor_associations`
