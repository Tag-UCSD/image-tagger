# Science Overview (v3.4.74 canonical line)

This document describes the science stack as it exists in the current `3.4.74`
repository state. The system is no longer just a legacy heuristics pipeline that
writes directly to `Validation`. It now has a canonical run model, dedicated
science-run persistence tables, and Explorer-facing APIs for queueing,
monitoring, and rendering canonical outputs.

## 1. Current pipeline shape

The main entry points are:

- `backend/science/pipeline.py`
- `backend/services/science_runs.py`
- `backend/api/v1_discovery.py`

The canonical flow is:

1. An image is queued for canonical processing via `ScienceRun` state in
   `backend/models/science_runs.py`.
2. The Explorer bootstrap endpoint, `POST /v1/explorer/science/bootstrap`,
   queues up to 500 missing runs for the active config/version.
3. A background worker processes `PENDING` runs with
   `SciencePipeline.process_image_canonical(...)`.
4. Outputs are persisted into:
   - `science_runs` for lifecycle state
   - `science_tags` for canonical tags
   - `science_artifacts` for structured JSON outputs
   - `validations` for persisted science attributes
5. The Explorer detail endpoint reads those canonical tables first and exposes:
   - `science_run`
   - `canonical_outputs_available`
   - canonical tags
   - canonical affordance and room summaries when present

The active science version is defined in `backend/services/science_runs.py`.
At the time of this documentation update it is `3.4.74-canonical-v2`.

## 2. Canonical config

`backend/services/science_runs.py` defines the authoritative canonical config.
The current defaults are:

- `enable_color = True`
- `enable_complexity = True`
- `enable_texture = True`
- `enable_fractals = True`
- `enable_spatial = True`
- `enable_affordance = True`
- `enable_room_detection = True`
- `enable_segmentation = False`
- `enable_cognitive = False`
- `enable_semantic = False`
- `enable_materials_basic = True`
- `enable_materials_vlm = False` by default unless enabled by env var
- `enable_clip_materials = False` by default unless enabled by env var

This means the canonical line currently emphasizes cheap deterministic
measurements plus room classification and material heuristics. Segmentation and
VLM-heavy enrichers are present in the codebase but are not part of the default
canonical run path.

## 3. What the canonical pipeline produces today

### Persisted science attributes

The pipeline still writes numeric attributes to `Validation` with a science
source. The current canonical set includes classic deterministic features such as
color, complexity, texture, fractals, spatial cues, and materials heuristics,
plus the new room and affordance keys.

### Canonical tags

Tag derivation now lives in `backend/science/tag_derivation.py`. The API layer
should not invent canonical tags on read.

Canonical tags currently include:

- `room_type.*` tags derived from Places365 coarse room predictions
- `affordance.<id>.(medium|high)` tags when affordance scores are available
- selected `style.*`, `cognitive.*`, and `biophilia.*` science attributes above
  threshold
- material tags from materials summaries when coverage is large enough
- object tags from segmentation summaries when segmentation is enabled

### Canonical artifacts

Structured artifacts are stored in `science_artifacts`. In the current line the
important artifact types are:

- `room_json`
- `affordance_json`
- `materials_json`

`room_json` is working end to end and backs the Explorer detail modal.
`affordance_json` is only present when affordance inference succeeds.
Segmentation artifacts are defined in the model contract but are not produced by
default because segmentation is off in `CANONICAL_CONFIG`.

## 4. Explorer integration

The Explorer now has two science-specific endpoints:

- `POST /v1/explorer/science/bootstrap`
- `GET /v1/explorer/science/status`

`bootstrap` queues missing runs and immediately returns summary counts.
Processing then continues in a background worker.

The detail endpoint,
`GET /v1/explorer/images/{image_id}/detail`, now exposes canonical state via:

- `science_run`
- `canonical_outputs_available`
- canonical tags from `science_tags`
- canonical affordance scores from `affordance_json` when present

The frontend detail modal has been updated to show:

- science run provenance
- canonical badge/state
- room type panel from canonical room tags

If canonical outputs are not yet available, the API still has a legacy fallback
path that synthesizes some tags from science attributes and the old
`affordance_runtime_v1` cache. That path remains for compatibility and should
not be treated as the canonical contract.

## 5. Backfill and operations

Large-scale processing is no longer dependent on the Explorer UI alone.

`backend/scripts/backfill_science_runs.py` can:

- print status
- process all pending runs
- process explicit IDs
- process ID ranges
- retry failed runs
- dry-run queue creation

This script runs the pipeline in-process and uses the same science-run service
layer as the API.

## 6. Current known gaps

The documentation should reflect the real current state rather than the desired
end state.

Known gaps today:

- Room detection is working and produces canonical tags plus `room_json`.
- Affordance model files are present, but the LightGBM pickle compatibility
  issue means canonical affordance inference is not reliable in the current
  environment.
- Segmentation exists in the codebase, but `enable_segmentation` is `False` in
  the active canonical config, so segmentation/object artifacts are not part of
  the default production path.
- The detail API still contains a legacy fallback path for pre-canonical science
  attributes and cached affordance payloads.

## 7. Testing status

The canonical line now has targeted tests in:

- `tests/test_tag_derivation.py`
- `tests/test_science_runs.py`

These cover:

- canonical tag derivation rules
- bootstrap/status endpoints
- detail endpoint canonical payload shape
- search payload science-run status exposure

## 8. Extension guidance

To add or change canonical outputs safely:

1. Update the analyzer or persistence logic in `backend/science/`.
2. Update `CANONICAL_CONFIG` or the version string if the active contract has
   changed.
3. Update `backend/science/tag_derivation.py` if the new output should create
   canonical tags.
4. Update registry/docs:
   - `backend/science/features_canonical.jsonl`
   - `contracts/attributes.yml`
   - `docs/SCIENCE_TAG_MAP.md`
5. Update Explorer API or frontend rendering only after the persistence contract
   is clear.

The important distinction in the `3.4.74` line is this: canonical science is now
an explicit persisted subsystem with versioned runs, not just a loose collection
of analyzer writes.
