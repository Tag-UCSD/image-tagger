# Engineering Brief, Plain-Language Version

| Term | meaning |
|---|---|
| Track | A work lane owned by one engineer or group. |
| Contract | The written agreement for API addresses, request shapes, response shapes, permissions, and shared data fields. |
| Smoke test | A short final check that proves the most important deployed user paths work. |
| JWT | A signed text token that says who a user is and what role they have. |
| Trust envelope | Extra fields attached to a model result that explain whether the result is validated, partly checked, or untested. |
| TRS | Tagging Registry System, an optional source of tag and attribute definitions. |
| Supabase Auth | The sign-in service used to create and verify user tokens. |
| Render | The hosting service planned for the Python API. |
| Vercel | The hosting service planned for the browser site. |

# List of Tasks

## Backend Phase 1

- A-1 Environment and secrets: move passwords, API secrets, database URLs, and runtime settings out of code and into environment variables. Test scripts may use simple local values while experimenting. The real app must stop with a clear error if a required secret is missing.
- A-2 Structured logging: replace scattered `print()` debugging with JSON logs that include request IDs, timing, user information, and status. This makes deployed problems easier to trace.
- A-3 Supabase JWT authentication: stop trusting user role text sent by the browser. Use signed login tokens created by Supabase Auth.
- A-4 Input validation and error handling: make every API address check incoming data and return errors in the same shape.
- A-7 ML trust envelope: attach trust information to every machine-learning result. The browser should show model outputs without claiming untested results are proven.
- A-10 Health check: make `/health` check the database and image storage, not only whether the Python process is running.
- A-11 Smoke-critical integration tests: test the backend paths used by Explorer, Workbench, Admin, and Monitor during the smoke test.
- A-12a Backend deployment configuration: add the files needed to deploy the Python API to Render.
- A-12b Backend live verification: a human checks the deployed Python API against real Render, Supabase, storage, database, and JWT setup.

## Frontend Phase 1

- B-1 Mock API client and fixtures: create one shared browser helper that can return fake data or call the real Python API.
- B-2 Shared design system: build shared buttons, inputs, error banners, loading placeholders, modals, pagination controls, and trust badges.
- B-3 Explorer journey: build public search, filters, pagination, image detail, science display, and trust badges.
- B-4 Workbench journey: build the labeling workflow: fetch one assigned task, show the right form, check the label, submit it, and move to the next item.
- B-5 Monitor journey: build supervisor views for labeling speed and inter-rater reliability. Handle empty data and unauthorized users clearly.
- B-6 Admin journey: build image upload, budget display, and kill-switch controls. Upload rules in the browser must match upload rules in the Python API.
- B-7 Responsive and accessibility audit: make all four browser apps usable on small screens and large screens, with labels, focus states, alternative text, and no serious accessibility problems.
- B-8a Frontend deployment configuration: add Vercel and workflow files so the browser workspace deploys as one site with routes for Explorer, Workbench, Monitor, and Admin.
- B-8b Frontend live verification: a human confirms the Vercel project, environment variables, GitHub connection, deployed API URL, and demo JWTs work.
- B-9 Mock-to-live swap: switch the browser apps from fake data to the deployed Python API and run the smoke test together.

## Coordination Tasks

- C-1 Smoke test runbook: write the exact final checklist for proving the deployed product works.
- C-1.5 Platform checklist: separate work that can be done in the repo from setup that must be done by a human in Render, Vercel, and Supabase.
- C-2 JWT provisioning: create short-lived role tokens for admin, tagger, and supervisor without committing secrets.
- Optional C-0 TRS contract diff: if TRS is used, compare it with the current contract and decide which changes are accepted, deferred, or rejected.

# How to Start

Read `docs/workplan/PRE_SPRINT.md` first. After the pre-sprint is complete, use:

- `docs/workplan/PLAN_BACKEND_PHASE1.md` for Backend Phase 1
- `docs/workplan/PLAN_FRONTEND_PHASE1.md` for Frontend Phase 1
- `docs/workplan/PLAN_TRS_INTEGRATION.md` only if the team chooses the optional TRS track

For v1, the controlling documents are:

- `docs/workplan/PRE_SPRINT.md`
- `docs/workplan/COORDINATION.md`
- `docs/CONTRACT.md`
- the track plan for the work you are doing

The product has four user journeys:

- Explorer: public browsing and image detail
- Workbench: human labeling
- Monitor: supervisor review
- Admin: uploads, budget controls, and a kill switch

Monitor and Admin may be more than the prototype needs right now. Discuss before cutting them from scope.

The backend is a Python application built with the Python package `fastapi`. Its image-analysis code lives under `backend/science/`. The frontend is a browser workspace built with the JavaScript package `react` under `frontend/apps/`.

For v1, done means:

- the project folder boundary is clean
- Backend Phase 1 and Frontend Phase 1 are complete
- the deployed smoke test passes
- Workbench, Monitor, and Admin can be opened with pre-issued role JWTs
- model outputs show honest trust statuses, even when formal evaluation is not finished

## Phase 1: Pre-Sprint

Target time: one full working day.

Goals:

- establish the target folder structure
- move old and out-of-scope material into `_archive/`
- commit `docs/CONTRACT.md`
- commit the planning documents needed before branching

Do not start Phase 2 until all pre-sprint exit checks pass.

## Phase 2: Parallel Phase 1 Work

Engineer A owns Backend Phase 1. The work is the deployable Python API foundation: environment variables, structured logs, Supabase JWT verification, input validation, shared error responses, trust envelopes, `/health`, smoke-critical integration tests, deployment files, and the smoke runbook.

Engineer B owns Frontend Phase 1. The work is the mock-first browser experience across Explorer, Workbench, Monitor, and Admin, including loading, empty, error, and unauthorized states; shared display components; responsive and accessible screens; demo access for protected routes; Vercel deployment; and the final switch from fake data to live data.

Engineer C, if assigned, owns the optional TRS track. TRS may provide generated local files at build time. It must not become a required running service for v1.

## Phase 3: Optional Follow-Up

Optional follow-up starts only after the v1 milestone is tagged or both engineers agree to continue. This work includes stronger monitoring, more tests, rate limiting, model evaluation, seeded monitor data, and browser polish.

None of the optional follow-up is required for the v1 smoke test.

## Documents and When to Use Them

| File | Owner | When to use it |
|---|---|---|
| `docs/CONTRACT.md` | All | Use as the source of truth for API addresses, permissions, shared types, trust fields, and environment variable names. |
| `docs/workplan/COORDINATION.md` | All | Use before branching and at sync points. |
| `docs/workplan/PRE_SPRINT.md` | All | Use first, before track work. |
| `docs/workplan/PLAN_BACKEND_PHASE1.md` | Engineer A | Use after pre-sprint for required v1 backend work. |
| `docs/workplan/PLAN_BACKEND_PHASE2.md` | Engineer A | Optional follow-up. |
| `docs/workplan/PLAN_FRONTEND_PHASE1.md` | Engineer B | Use after pre-sprint for required v1 frontend work. |
| `docs/workplan/PLAN_FRONTEND_PHASE2.md` | Engineer B | Optional follow-up. |
| `docs/workplan/PLAN_TRS_INTEGRATION.md` | Engineer C | Use only if the team wants TRS as a build-time source. |

Anything under `_archive/` is historical unless a current plan explicitly says otherwise.

If you use an LLM coding agent, give it the contract, the relevant plan file, and any coordination or human-gate instructions. Ask it to complete tasks in order and verify each acceptance criterion before moving on.

## Coordination Tips

- Do not commit directly to `main`.
- Finish the pre-sprint merge on `main` before track work starts.
- Branch Backend Phase 1 as `track-a-backend-phase1`.
- Branch Frontend Phase 1 as `track-b-frontend-phase1`.
- If TRS is used, branch it as `track-c-trs-integration`.
- Use short-lived feature branches under each track branch.
- Treat `docs/CONTRACT.md` as the source of truth for shared behavior.
- Sync at these points: after the pre-sprint contract is committed, when the trust-envelope shape is final, and during the final mock-to-live session.

## First Steps

1. Open `docs/workplan/PRE_SPRINT.md` and complete the pre-sprint sequence together.
2. Read `docs/CONTRACT.md`, `docs/workplan/PLAN_BACKEND_PHASE1.md`, and `docs/workplan/PLAN_FRONTEND_PHASE1.md` before branching.
3. After branching, Engineer A starts with A-1 and Engineer B starts with B-1. If assigned, Engineer C starts with TRS C-1.
