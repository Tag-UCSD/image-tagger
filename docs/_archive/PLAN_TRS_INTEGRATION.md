# TRS INTEGRATION TRACK

**Owner:** Engineer C. **Scope:** integrate `TRS_v1.1` as a
build-time source of canonical registry and contract artifacts for the
image-tagger repo. **Out of scope:** making TRS a runtime dependency,
shipping the TRS API or Streamlit UI as part of v1, changing frontend
journeys directly, or blocking the Phase 1 smoke flow on TRS service
availability.

Required coordination note: this track is subordinate to
`docs/CONTRACT.md`, `docs/workplan/COORDINATION.md`, and the active
Phase 1 plans. If a TRS-derived artifact conflicts with the committed
contract, Engineer C proposes a contract update and handoff; Engineer C
does not silently overwrite the app contract by script.

## Track End State

The TRS integration track is complete when:

- the image-tagger repo has one explicit, version-pinned ingestion path
  from the TRS registry bundle into repo-local artifacts
- canonical attribute and feature metadata needed by image-tagger can be
  derived from the TRS snapshot without calling TRS at runtime
- a machine-checkable validation step proves the repo-local derived
  artifacts are still in sync with the pinned TRS source snapshot
- Engineer A can consume the derived backend artifact(s) in
  `backend/science/features_registry.py` or adjacent code without
  reverse-engineering TRS internals
- Engineer B can consume any contract-approved shared type or label
  changes without reading TRS directly

This track does **not** claim:

- that v1 must deploy or run the TRS FastAPI service
- that frontend apps must browse the TRS registry directly
- that the smoke runbook depends on TRS health
- that TRS becomes the runtime source of truth during Phase 1

## Integration Principles

- Treat `TRS_v1.1/core/trs-core/v0.2.8/registry/cnfa_tag_registry_canonical_v0.2.8.yaml`
  as the upstream source snapshot for this track.
- Produce repo-local, inspectable outputs under the active image-tagger
  tree; do not make backend or frontend import from the live `TRS_v1.1`
  application package at request time.
- Favor one-way generation over shared mutable state. The image-tagger
  app consumes exported artifacts, not TRS runtime code paths.
- Keep the seam narrow: canonical keys, names, categories, type hints,
  allowed values, and related metadata needed by the app contract. Do
  not attempt to absorb all TRS concepts into v1.
- Any contract-shape change that affects frontend mocks, shared types,
  backend schemas, or smoke behavior must be proposed through
  `docs/CONTRACT.md` and the owning track, not landed implicitly.

## Task List

#### Task C-1: Source Audit and Seam Definition
- **Goal:** define exactly which TRS artifacts matter to image-tagger
  and what the export seam is.
- **Files to create or modify:** `docs/TRS_SEAM.md` (new),
  `docs/workplan/PLAN_TRS_INTEGRATION.md`.
- **Implementation notes:** Inspect the vendored TRS registry bundle,
  bundled contracts, and validation scripts. Document the source files,
  pinned version, fields to consume, fields to ignore for v1, and the
  target image-tagger consumers. Include a mapping table from TRS
  concepts to current image-tagger concepts such as attribute key,
  display name, category, value type, and any canonical allowed values.
- **Acceptance criteria:** `docs/TRS_SEAM.md` exists and names the exact
  upstream TRS source files, the pinned TRS version, the repo-local
  outputs to generate, and whether each downstream consumer is Engineer
  A, Engineer B, or both; the document states explicitly that TRS is a
  build-time source and not a Phase 1 runtime dependency.
- **Depends on:** pre-sprint only.

#### Task C-2: Build-Time Export Pipeline
- **Goal:** generate repo-local canonical artifacts from the pinned TRS
  source snapshot.
- **Files to create or modify:** `backend/scripts/export_trs_registry.py`
  (new), `backend/science/data/trs_registry_snapshot.json` (new),
  `frontend/shared/src/generated/trsRegistry.ts` (new or equivalent),
  `.gitignore` if required for generated intermediates.
- **Implementation notes:** Implement a one-way export command that reads
  the pinned TRS YAML and any required TRS contract metadata, then emits
  stable, committed artifacts for image-tagger consumption. Outputs must
  be deterministic and sorted so diffs are reviewable. Do not import
  from `TRS_v1.1/backend/app/*` at runtime. If generated frontend data is
  not yet needed in Phase 1, emit the artifact anyway but keep its use
  optional until the contract owners approve adoption.
- **Acceptance criteria:** running the documented export command from
  repo root regenerates the committed artifacts with no manual edits;
  re-running it without upstream changes produces no diff; the exported
  JSON/TS artifacts are stable, human-inspectable, and derived from the
  pinned TRS snapshot rather than hand-maintained copies.
- **Depends on:** C-1.

#### Task C-3: Contract Diff and Adoption Proposal
- **Goal:** make any TRS-driven contract impact explicit before A or B
  consume it.
- **Files to create or modify:** `docs/TRS_CONTRACT_DIFF.md` (new),
  `docs/CONTRACT.md` only if approved and necessary.
- **Implementation notes:** Compare the exported TRS-derived artifact
  against the current committed contract and current frontend/backend
  assumptions. Categorize differences as: safe now, safe post-v1, or
  incompatible with current Phase 1. Engineer C proposes changes; the
  owning track accepts or defers them. This task is where contract drift
  becomes visible instead of leaking into implementation code.
- **Acceptance criteria:** `docs/TRS_CONTRACT_DIFF.md` exists and
  enumerates concrete differences with a disposition for each; any
  updates to `docs/CONTRACT.md` are narrow, reviewed, and traceable to
  specific accepted diffs; no unreviewed contract-shape change is hidden
  inside generated artifacts or code.
- **Depends on:** C-2.

#### Task C-4: Validation and CI Guardrail
- **Goal:** prevent repo-local TRS-derived artifacts from drifting away
  from the pinned upstream snapshot.
- **Files to create or modify:** `backend/scripts/validate_trs_sync.py`
  (new), `.github/workflows/test_backend.yml` or a dedicated validation
  workflow, `docs/TRS_SEAM.md`.
- **Implementation notes:** Add one concrete validation command that
  checks the committed exported artifacts against the pinned TRS input.
  The check must fail loudly when the generated outputs are stale or when
  manual edits were made to generated artifacts. Keep the workflow
  deterministic and independent of running the TRS service.
- **Acceptance criteria:** the repo contains one documented validation
  command and one CI invocation for it; intentionally modifying a
  generated artifact without re-exporting causes the validation step to
  fail; the validation step does not require Docker, the TRS UI, or the
  TRS API to be running.
- **Depends on:** C-2.

#### Task C-5: Handoff to Backend and Frontend Owners
- **Goal:** give Engineers A and B clear adoption boundaries that do not
  require them to become TRS experts.
- **Files to create or modify:** `docs/TRS_HANDOFF.md` (new),
  `docs/workplan/COORDINATION.md`.
- **Implementation notes:** Document the exact backend adoption point
  for Engineer A, such as a generated registry snapshot or normalized
  metadata module, and the exact frontend adoption point for Engineer B,
  such as generated shared labels or enum/type data. Include what is
  required for Phase 1, what is optional, and what is explicitly deferred
  until after the v1 tag.
- **Acceptance criteria:** `docs/TRS_HANDOFF.md` exists and contains one
  short section for Engineer A and one for Engineer B with concrete file
  paths, adoption timing, and non-goals; Engineer A can proceed on A-7
  without reading TRS internals, and Engineer B can proceed on B-1/B-3
  without direct dependency on `TRS_v1.1`.
- **Depends on:** C-3, C-4.

## Recommended Timing

- Start this track immediately after pre-sprint and branch from the same
  post-pre-sprint `main` as Tracks A and B.
- C-1 and C-2 should finish before Engineer A finalizes Task A-7 and
  before Engineer B hardens long-lived mock fixtures or shared types.
- C-3 is the decision gate: accepted diffs may flow into the contract;
  deferred diffs wait until after the v1 tag.
- C-4 can land in parallel with A-7 and B-1 once the export format is
  stable.
- C-5 must land before the team treats the contract and derived artifacts
  as frozen for the final smoke path.

## Branching and Ownership

- Recommended branch: `track-c-trs-integration`
- Suggested feature branches: `track-c/trs-seam`,
  `track-c/trs-export`, `track-c/trs-validate`
- Engineer C owns TRS-source inspection, export tooling, generated
  artifacts, and sync validation.
- Engineer A owns backend runtime adoption of approved TRS-derived
  artifacts.
- Engineer B owns frontend adoption of approved contract/type changes.

## Non-Blocking Rule

This track must remain separable from the v1 smoke path. If the TRS
export pipeline slips, Engineers A and B continue against the committed
`docs/CONTRACT.md` and current repo-local artifacts. The TRS track may
improve canonicalization and reduce future drift, but it must not become
an implicit runtime or deployment prerequisite for Phase 1.
