# WORKPLAN 2 TRACK MAP

This folder breaks Workplan 2 into three fully parallel work tracks:

- Track A: image sets and provenance
- Track B: latent variables and observations
- Track C: GUI updates and shared client work

Each track is written in the same execution-plan style as `docs/workplan`: owner, scope, end state, task list, implementation notes, acceptance criteria, and dependencies.

## Parallel Ownership

| Track | Objective | Primary Files |
|---|---|---|
| Track A | Named image sets, provenance, import APIs, set-filtered Explorer responses | `backend/models/`, `backend/schemas/`, `backend/services/`, `backend/api/`, backend tests |
| Track B | Six latent variables, observation persistence, effect mapping, science-run integration | `backend/science/`, `backend/services/`, `backend/data/`, backend tests |
| Track C | Explorer/Admin/Workbench/Monitor GUI updates and shared frontend API/mocks | `frontend/shared/`, `frontend/apps/`, frontend tests |

## Coordination Rules

- Tracks A and B may both need a latent/image-set relationship. Track B should keep `image_set_id` optional until Track A lands.
- Track C should start with mocks and not wait for backend endpoints.
- Public API changes must be reflected in `docs/CONTRACT.md`.
- Do not create a standalone HTML viewer.
- Do not write upstream Knowledge Atlas deliverables.

## Integration Order

1. Merge Track A image-set models and endpoints.
2. Merge Track B latent observation persistence, detectors, and effect mapping.
3. Merge Track C mock-driven UI work.
4. Run Track C against the live local backend and fix contract mismatches in the shared client or backend schemas.

