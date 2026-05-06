# TRS Integration Track, Plain-Language Version

| Term | Plain meaning |
|---|---|
| TRS | Tagging Registry System, an optional source of tag and attribute definitions. |
| Integration | Connecting one system to another in a controlled way. |
| Build-time | During setup or generation before the app runs for users. |
| Runtime | While the deployed app is running for users. |
| Artifact | A generated file that other code can read. |
| Snapshot | A fixed saved copy of source data. |
| Contract | The written agreement for API addresses, data shapes, permissions, and shared fields. |
| Drift | A generated file no longer matching its source. |
| CI | GitHub automation that runs checks when code changes. |
| Handoff | Clear instructions that let another engineer use the result without learning all internal details. |
| Docker | A tool for packaging an app so it runs the same way on a server. |
| Streamlit | A Python package used to build simple data apps. |

**Owner:** Engineer C.

**Scope:** use `TRS_v1.1` as a build-time source for local image-tagger registry and contract artifacts.

**Out of scope:** making TRS a required running service, shipping the TRS API or Streamlit UI in v1, changing browser journeys directly, or blocking the Phase 1 smoke test on TRS service availability.

This track is subordinate to `docs/CONTRACT.md`, `docs/workplan/COORDINATION.md`, and the active Phase 1 plans. If a TRS-derived file conflicts with the committed contract, Engineer C proposes a contract update. Engineer C must not silently overwrite the app contract with a script.

## Track End State

The TRS track is complete when:

- the image-tagger repo has one version-pinned command that reads the TRS registry snapshot
- image-tagger can generate local artifacts from TRS without calling TRS while the app runs
- a validation command proves generated artifacts still match the pinned TRS source
- Engineer A can use backend artifacts without reverse-engineering TRS
- Engineer B can use approved shared type or label changes without reading TRS directly

This track does not claim:

- v1 must deploy or run the TRS Python API
- browser apps must browse TRS directly
- the smoke runbook depends on TRS health
- TRS becomes the runtime source of truth during Phase 1

## Integration Principles

- Treat `TRS_v1.1/core/trs-core/v0.2.8/registry/cnfa_tag_registry_canonical_v0.2.8.yaml` as the upstream source snapshot.
- Generate local, reviewable files inside the image-tagger repo.
- Do not make backend or frontend code import from the live TRS application at request time.
- Prefer one-way generation over shared mutable state.
- Keep the shared boundary narrow: keys, names, categories, type hints, allowed values, and metadata needed by the current contract.
- Any change that affects browser mocks, shared types, backend schemas, or smoke behavior must be proposed through `docs/CONTRACT.md`.

## Task C-1: Source Audit and Boundary Definition

Goal: define exactly which TRS files matter and what will be exported.

Files: `docs/TRS_SEAM.md`, `docs/workplan/PLAN_TRS_INTEGRATION.md`.

Instructions:

- Inspect the vendored TRS registry bundle, contracts, and validation scripts.
- Document source files, pinned version, fields to use, and fields to ignore for v1.
- Document the target image-tagger consumers.
- Include a mapping table from TRS concepts to image-tagger concepts such as attribute key, display name, category, value type, and allowed values.

Done when `docs/TRS_SEAM.md` names exact upstream files, pinned TRS version, generated local outputs, and downstream owners, and states that TRS is build-time only for Phase 1.

## Task C-2: Build-Time Export Pipeline

Goal: generate local image-tagger artifacts from the pinned TRS snapshot.

Files: `backend/scripts/export_trs_registry.py`, `backend/science/data/trs_registry_snapshot.json`, `frontend/shared/src/generated/trsRegistry.ts`, and `.gitignore` if needed.

Instructions:

- Write one export command that reads the pinned TRS YAML and needed TRS metadata.
- Generate stable committed artifacts for image-tagger.
- Sort output so Git diffs are easy to review.
- Do not import from `TRS_v1.1/backend/app/*` while the app is running.
- If browser-generated data is not needed yet, still generate it, but keep its use optional until contract owners approve adoption.

Done when running the export command regenerates the artifacts with no manual edits, re-running without source changes produces no diff, and artifacts are human-inspectable.

## Task C-3: Contract Diff and Adoption Proposal

Goal: make TRS-driven contract effects visible before Engineers A or B use them.

Files: `docs/TRS_CONTRACT_DIFF.md`, and `docs/CONTRACT.md` only if approved.

Instructions:

- Compare generated TRS artifacts with the current image-tagger contract.
- Mark differences as safe now, safe after v1, or incompatible with Phase 1.
- Engineer C proposes changes.
- The owning track accepts or defers them.
- Do not hide contract changes inside generated files or implementation code.

Done when `docs/TRS_CONTRACT_DIFF.md` lists concrete differences and each has a decision.

## Task C-4: Validation and CI Guardrail

Goal: prevent generated TRS artifacts from drifting away from their source.

Files: `backend/scripts/validate_trs_sync.py`, a GitHub workflow, and `docs/TRS_SEAM.md`.

Instructions:

- Add one validation command that compares committed generated files with the pinned TRS input.
- Make the command fail clearly when generated files are stale or manually edited.
- Keep the check deterministic.
- Do not require Docker, the TRS UI, or the TRS API to run.

Done when the repo contains a documented validation command and CI runs it, and intentionally editing a generated artifact makes the check fail.

## Task C-5: Handoff to Backend and Frontend Owners

Goal: let Engineers A and B use the result without becoming TRS experts.

Files: `docs/TRS_HANDOFF.md`, `docs/workplan/COORDINATION.md`.

Instructions:

- Document the exact backend adoption point for Engineer A.
- Document the exact frontend adoption point for Engineer B.
- State what is required for Phase 1, what is optional, and what is deferred until after the v1 tag.

Done when `docs/TRS_HANDOFF.md` has one short section for Engineer A and one for Engineer B, with file paths, timing, and non-goals.

## Recommended Timing

- Start after pre-sprint from the same post-pre-sprint `main` as Tracks A and B.
- Finish C-1 and C-2 before Engineer A finalizes A-7 and before Engineer B freezes long-lived mock fixtures or shared types.
- Use C-3 as the decision point for contract changes.
- C-4 can land in parallel once the export format is stable.
- C-5 must land before the team treats contract and generated artifacts as final for the smoke path.

## Branching and Ownership

- Recommended branch: `track-c-trs-integration`
- Suggested feature branches: `track-c/trs-seam`, `track-c/trs-export`, `track-c/trs-validate`
- Engineer C owns TRS inspection, export tooling, generated artifacts, and sync validation.
- Engineer A owns backend runtime adoption of approved TRS-derived artifacts.
- Engineer B owns frontend adoption of approved contract or type changes.

## Non-Blocking Rule

This track must remain separate from the v1 smoke path. If the TRS export work slips, Engineers A and B continue using `docs/CONTRACT.md` and current local artifacts.
