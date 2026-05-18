# TRACK B: LATENT VARIABLES AND OBSERVATIONS

**Owner:** Science/backend agent. **Scope:** six latent social-spatial detectors, latent observation storage, detector evidence, effect mapping, science-run integration, canonical tag promotion, and backend tests. **Out of scope:** image-set import UI, frontend component implementation, migrations owned by Track A except shared relationships, and standalone HTML viewers.

Track B can run in parallel with Track A and Track C. If Track A has not landed, keep `image_set_id` optional and attach it later. Track C should use mocked latent payloads until this track is live.

## Track B End State

Track B is complete when:

- six latent variables run through one stable detector interface
- each detector returns value, value type, confidence, evidence, and detector version
- observations persist without duplicate accumulation
- canonical science runs can produce six latent observations for a processed image
- high latent values can become canonical tags
- effect domains map to latent tags with short mechanism explanations
- backend APIs can return latent observations and linked effects to Explorer
- tests cover ranges, evidence, persistence, science-run integration, and effect mapping

Track B does **not** include:

- training neural networks
- adding heavyweight ML dependencies
- frontend visual design
- research-grade validation claims

## Selected Detectors

Implement these six tags:

- `social.sociopetal_seating`
- `social.shared_attention_anchor`
- `social.interactional_visibility`
- `spatial.prospect`
- `social.chance_encounter_potential`
- `social.disengagement_ease`

All values use `value_type: "ordinal"` and a `0..4` range. Proxy-only confidence should usually be `0.2..0.4`.

## Task List

#### Task B2-1: Add Latent Observation Model And Schema
- **Goal:** Store latent detector outputs as first-class records.
- **Files to create or modify:** `backend/models/`, `backend/schemas/`, migration helper, backend tests.
- **Implementation notes:** Add `LatentObservation` with `image_id`, optional `image_set_id`, optional `science_run_id`, `tag_id`, `value`, `value_type`, `confidence`, `evidence`, `detector_version`, timestamps. Validate `value` in `0..4`, `confidence` in `0..1`, and JSON evidence.
- **Acceptance criteria:** Tests create, reload, and validate observations. Invalid value or confidence is rejected.
- **Depends on:** existing database model setup.

#### Task B2-2: Define Detector Result Interface
- **Goal:** Make all detectors return the same typed shape.
- **Files to create or modify:** new `backend/science/context/latent_social.py` or equivalent, tests.
- **Implementation notes:** Add `LatentObservationResult`. Add `DETECTOR_VERSION = "latent-social-v1"`. Add `run_latent_social_detectors(frame)` returning exactly six results. Keep this independent from FastAPI and database sessions.
- **Acceptance criteria:** A synthetic `AnalysisFrame` produces six known tag IDs, in-range values, in-range confidence, and non-empty evidence.
- **Depends on:** B2-1 can run in parallel.

#### Task B2-3: Extract Shared Proxy Features
- **Goal:** Compute cheap deterministic features used by the six detectors.
- **Files to create or modify:** latent detector module or helper under `backend/science/spatial/`.
- **Implementation notes:** Use `AnalysisFrame.gray_image`, `edges`, `lab_image`, optional `depth_map`, `attributes`, and `metadata`. Useful proxies include edge density, central edge density, brightness mean/variance, estimated openness, depth spread, lower-frame path complexity, and available segmentation/material hints. Do not load new models.
- **Acceptance criteria:** Synthetic-frame tests show stable features and no crash when depth or metadata is missing.
- **Depends on:** B2-2.

#### Task B2-4: Implement Six Detectors
- **Goal:** Convert proxy/intermediate features into ordinal latent observations.
- **Files to create or modify:** latent detector module and unit tests.
- **Implementation notes:** Keep formulas auditable. Include evidence keys such as `openness_score`, `edge_density`, `central_focus_proxy`, `depth_source`, `path_complexity_proxy`, `segmentation_source`, and `proxy_version`. Avoid making all detectors return the same value.
- **Acceptance criteria:** Tests cover open/bright, cluttered/high-edge, and missing-depth frames. Values stay in range. Confidence decreases when evidence is weak. Evidence includes the major inputs used by each score.
- **Depends on:** B2-3.

#### Task B2-5: Add Latent Persistence Service
- **Goal:** Persist detector results idempotently.
- **Files to create or modify:** `backend/services/latent_observations.py`, backend tests.
- **Implementation notes:** Add a service that stores results by image, optional image set, optional science run, tag ID, and detector version. Prefer replacing/updating prior results for the same active run and tag rather than creating duplicates.
- **Acceptance criteria:** Persisting the same six results twice updates existing rows or leaves exactly six rows, not twelve. Query helpers fetch by image and, when available, image set.
- **Depends on:** B2-1, B2-2.

#### Task B2-6: Integrate With Canonical Science Runs
- **Goal:** Let canonical processing produce latent observations.
- **Files to create or modify:** `backend/science/pipeline.py`, `backend/services/science_runs.py`, tests.
- **Implementation notes:** Add `enable_latent_social` to `SciencePipelineConfig`, `to_dict()`, and canonical config. Run latents after core spatial/material analyzers populate the frame. Persist through the latent service. If the canonical config changes, bump `ACTIVE_SCIENCE_VERSION`.
- **Acceptance criteria:** A fixture pipeline run produces six observations and still marks the science run completed. Failure paths still mark the run failed.
- **Depends on:** B2-4, B2-5.

#### Task B2-7: Promote High Latents Into Tags
- **Goal:** Let high latent outputs appear in existing tag surfaces.
- **Files to create or modify:** `backend/science/tag_derivation.py`, tests.
- **Implementation notes:** Add `derive_latent_observation_tags()`. Promote observations with `value >= 2.5`. Use readable labels from tag IDs. Namespace should be `social` or `spatial`. Use observation confidence.
- **Acceptance criteria:** Value `3.0` creates a canonical tag. Value `1.0` does not. Existing tag derivation still passes.
- **Depends on:** B2-6.

#### Task B2-8: Add Effect Mapping
- **Goal:** Link latent tags to human effect domains and mechanism text.
- **Files to create or modify:** `backend/data/effect_tag_mapping.json`, loader/helper module, tests.
- **Implementation notes:** Add domains `cognitive`, `affective`, `behavioral`, `social`, `physiological`, `neural`, `health`. For v1, use manual mapping from `docs/workplan_2/OVERVIEW.md` and Workplan 2. Add helper functions from tag to domains and domain to tags.
- **Acceptance criteria:** Tests prove social/cognitive/affective/behavioral mappings return expected tags. Unknown domains return empty lists. Every mapped tag is one of the six selected latent IDs.
- **Depends on:** B2-2.

#### Task B2-9: Extend Explorer Latent Responses
- **Goal:** Return latent observations and linked effects through backend Explorer APIs.
- **Files to create or modify:** `backend/api/v1_discovery.py`, discovery schemas, latent/effect services, integration tests.
- **Implementation notes:** Add latent observations and linked effects to image detail. Extend search with `latent_tag`, `effect_domain`, and `min_value`. Coordinate with Track A so `image_set` combines correctly with these filters.
- **Acceptance criteria:** Detail returns six observations with evidence and detector version. Search by `latent_tag` and `min_value` returns only matching images. Search by `effect_domain=social` uses effect mapping.
- **Depends on:** B2-5, B2-8. Coordinate with Track A for combined filters.

#### Task B2-10: Update Contract Docs
- **Goal:** Document latent payloads and filters.
- **Files to create or modify:** `docs/CONTRACT.md`.
- **Implementation notes:** Add the six tag IDs, `0..4` ordinal rule, confidence/evidence fields, linked effect shape, and search params `latent_tag`, `effect_domain`, `min_value`.
- **Acceptance criteria:** Contract contains enough shape detail for Track C to remove mocks safely.
- **Depends on:** B2-9.

## Track B Smoke Check

Run one fixture image through canonical science with latent social enabled. Confirm six observations persist. Confirm a high-value observation promotes to a tag. Confirm image detail returns latent observations and linked effects.

