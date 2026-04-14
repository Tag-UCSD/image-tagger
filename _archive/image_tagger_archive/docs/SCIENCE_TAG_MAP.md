# Science Tag Coverage Map (v3.4.74 canonical line)

This document is a practical coverage map for the canonical science outputs that
matter operationally today. It is intentionally narrower than the full feature
registry in `backend/science/features_canonical.jsonl`.

## 1. Canonical tag producers

The current canonical tag rules live in `backend/science/tag_derivation.py`.
They produce tags from persisted science outputs, not from UI-only inference.

## 2. Tags that are live in the current config

### Room tags

- Source: `RoomDetectionAnalyzer` / Places365
- Persistence:
  - attribute keys: `room.type_coarse`, `room.type_coarse_confidence`,
    `room.type_fine_confidence`
  - artifact: `room_json`
  - canonical tag namespace: `room_type.*`
- Status: live in the default canonical config

Emission rule:

- Emit one `room_type.<label>` tag when top coarse-room confidence is at least
  `0.20`.

Example:

- `room_type.lobby`
- `room_type.kitchen`
- `room_type.bedroom`

### Science-attribute tags

- Source namespaces:
  - `style.*`
  - `cognitive.*`
  - `biophilia.*`
- Status: live when those attributes are present

Emission rule:

- Promote the attribute to a canonical tag when value is at least `0.5`.

### Material tags

- Source: `materials_json`
- Canonical tag namespace: `material.*`
- Status: live only when material summaries are present

Emission rule:

- Emit a material tag when estimated coverage is at least `0.04`.

Example:

- `material.wood`
- `material.stone`

## 3. Tags defined but not currently reliable in the default runtime

### Affordance tags

- Source keys:
  - `affordance.L059`
  - `affordance.L079`
  - `affordance.L091`
  - `affordance.L130`
  - `affordance.L141`
- Canonical tag namespace:
  - `affordance.<id>.medium`
  - `affordance.<id>.high`
- Artifact: `affordance_json`

Emission thresholds:

- `>= 5.5` → `high`
- `>= 3.5` → `medium`
- lower scores do not emit a tag

Runtime status:

- The derivation rules are implemented.
- The current environment still has a LightGBM pickle compatibility issue, so
  affordance outputs should be treated as partially implemented operationally.

## 4. Tags gated behind disabled segmentation

### Object tags

- Source: segmentation/object summaries
- Canonical tag namespace: `object.*`
- Status: implemented in derivation logic but not active in the default
  canonical config because `enable_segmentation = False`

Emission rule:

- object coverage at least `0.01`
- object confidence at least `0.30`

## 5. Explorer/UI contract

The Explorer detail API prefers canonical tags from `science_tags`.
Only when canonical outputs are unavailable does it fall back to legacy
read-time promotion from older science attributes.

This means:

- `science_tags` is the source of truth for canonical tags
- `Validation` remains the source of truth for numeric science attributes
- `science_artifacts` is the source of truth for structured summaries

## 6. Known mismatch to watch

The code and migrations now know about room and affordance canonical keys, but
the broader historical feature registry still contains many legacy aspirational
entries. When adding new canonical attributes, update all of the following in
the same change:

- `backend/science/features_canonical.jsonl`
- `contracts/attributes.yml`
- this file

If those three drift apart, the repo becomes hard to reason about.
