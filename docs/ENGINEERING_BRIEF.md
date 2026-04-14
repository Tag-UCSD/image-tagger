---
editor_options: 
  markdown: 
    wrap: 72
---

# Engineering Brief

Start here: read `docs/workplan/PRE_SPRINT.md` first, then execute from
`docs/workplan/PLAN_BACKEND_PHASE1.md` and
`docs/workplan/PLAN_FRONTEND_PHASE1.md` after the pre-sprint is
complete. If the team chooses to integrate the Tagging Registry System
(TRS), execute `docs/workplan/PLAN_TRS_INTEGRATION.md` in parallel only
after pre-sprint. For v1, execution authority is shared across
`docs/workplan/PRE_SPRINT.md`, `docs/workplan/COORDINATION.md`,
`docs/CONTRACT.md`, and the relevant track plan file you are executing.

The product currently has four user journeys: Explorer for public browse
and image detail, Workbench for human-in-the-loop tagging, Monitor for
supervisor oversight, and Admin for uploads, budget controls, and a
kill-switch. I think Monitor and Admin may be less than necessary for
our prototype at this point, but we can discuss.

The backend is a FastAPI application with a science pipeline under
`backend/science/`, and the frontend is a React monorepo under
`frontend/apps/`. For v1, "done" means the repo boundary is cleaned up,
Backend Phase 1 and Frontend Phase 1 are complete, the live smoke
runbook passes, the three protected frontend journeys are reachable
through a minimal demo-access mechanism backed by pre-issued role JWTs,
and ML outputs are surfaced with honest trust-envelope statuses even
where formal evaluation has not yet been completed.

## The Three Phases of Work

**Phase 1 — Pre-Sprint (both engineers)**

Time-box target: one full working day.

Goals: - establish the target folder structure by promoting the active
project to repo root and moving historical and out-of-scope material
into `_archive/` - commit the shared contract in `docs/CONTRACT.md` and
the canonical docs needed for branching - establish the four phase plan
documents that define the v1 scope and optional follow-up scope

Exit criteria checklist: - `git log --oneline -1` on `main` shows the
pre-sprint merge commit and both engineers have pulled it -
`/docs/CONTRACT.md` exists on `main` and both engineers have read it end
to end - `docs/ARCHITECTURE.md` exists on `main`, and repo-root
`README.md` points to it and the contract - `ls` at repo root shows no
stray changelogs, no sibling projects, and no `archive/` outside
`_archive/` - two feature branches exist: `track-a-backend-phase1` and
`track-b-frontend-phase1`, both branched from the post-pre-sprint `main`

Do not begin Phase 2 until every exit criterion above is checked off.

**Phase 2 — Parallel Phase 1 Execution (split, with optional Track C)**

Engineer A owns Backend Phase 1. The scope is the deployable backend
foundation: environment and secrets management, structured logging,
Supabase JWT auth, input validation and error handling, the ML trust
envelope, basic `/health`, smoke-critical integration tests for
explorer, workbench, admin, and monitor, deployment configuration, and
the shared smoke runbook. Prometheus `/metrics`, full Alembic
replacement, Sentry integration, GitHub deploy automation, the dedicated
monitor seed workflow, formal model evaluation, rate limiting, and any
broader test hardening beyond smoke-critical coverage are explicitly
deferred to Phase 2. The Phase 1 monitor outcome is limited to the
contracted route behavior and UI handling; Phase 1 does not require
seeded IRR data in the deployed environment.

Engineer B owns Frontend Phase 1. The scope is the mock-first frontend
across the four user journeys, including contracted loading, empty,
error, and unauthorized states, a shared design system, responsive and
accessible interaction flows, a minimal demo-access mechanism for the
protected journeys, Vercel deployment, and the final mock-to-live swap.
Frontend Phase 1 does not include a sign-in UI; protected routes are
exercised through role-scoped pre-issued JWTs configured in the deployed
frontend environment.

Engineer C, if assigned, owns the TRS integration track. Its scope is a
non-blocking, build-time-only ingestion path from the pinned
`TRS_v1.1` registry bundle into repo-local artifacts that Backend Phase
1 and Frontend Phase 1 can consume after review. Track C does not make
TRS a runtime dependency for v1, does not add the TRS API or UI to the
smoke path, and does not override `docs/CONTRACT.md` without explicit
review.

**Phase 3 — Optional Follow-Up (both engineers if chosen)**

Optional Phase 2 work begins only after the v1 milestone is tagged or
both engineers explicitly agree to continue. Backend Phase 2 covers
Prometheus `/metrics`, full Alembic replacement, broader
integration-test hardening, Sentry integration, GitHub deploy
automation, the dedicated monitor seed workflow, rate limiting, and
formal ML evaluation. Frontend Phase 2 covers optional workflow and
polish enhancements such as richer region tooling and explorer
performance polish. None of this work is required for the v1 smoke flow.

## Your Documents and How to Use Them

| File | Owner | When to use it |
|-----------------|-----------------|--------------------------------------|
| `docs/CONTRACT.md` | All | Read during pre-sprint and use as the source of truth for endpoint shapes, auth headers, shared types, ML trust envelope fields, and environment variable names. |
| `docs/workplan/COORDINATION.md` | All | Read before branching and revisit at each sync point to follow the seam analysis, branching strategy, review boundaries, and integration plan. |
| `docs/workplan/PRE_SPRINT.md` | All or Brandon + Tag while Ethan finishes current models | Use first, before any track work, to execute the repo restructure, branch-readiness steps, and exit-criteria checklist. |
| `docs/workplan/PLAN_BACKEND_PHASE1.md` | Engineer A | Use after pre-sprint for the required v1 backend work. |
| `docs/workplan/PLAN_BACKEND_PHASE2.md` | Engineer A | Would be nice, but out of scope for now |
| `docs/workplan/PLAN_FRONTEND_PHASE1.md` | Engineer B | Use after pre-sprint for the required v1 frontend work. |
| `docs/workplan/PLAN_FRONTEND_PHASE2.md` | Engineer B | Would be nice, but out of scope for now |
| `docs/workplan/PLAN_TRS_INTEGRATION.md` | Engineer C | Use after pre-sprint only if the team wants TRS integrated as a build-time artifact source without making it part of the Phase 1 runtime boundary. |

Anything under root-level `_archive/` is historical material only. Do
not use archived docs as execution instructions, source-of-truth plans,
or acceptance criteria. The only exception is the explicitly selected
TRS source snapshot under `TRS_v1.1/` when working from
`docs/workplan/PLAN_TRS_INTEGRATION.md`; even then, TRS is an upstream
build-time input, not a runtime authority for Phase 1.

If you are using an LLM coding agent, do not paste only a single plan
file. Give the agent `docs/CONTRACT.md`, the relevant Phase 1 plan file,
and any required coordination or human-gate instructions from
`docs/workplan/COORDINATION.md` and `docs/workplan/PRE_SPRINT.md`, then
work through the agent-executable tasks in order and confirm each
acceptance criterion before moving to the next.

## Coordination Tips

-   Never commit directly to `main`.
-   Finish the pre-sprint merge on `main` before either engineer starts
    track work.
-   Branch the two main Phase 1 tracks from post-pre-sprint `main` as
    `track-a-backend-phase1` and `track-b-frontend-phase1`.
-   If Track C is in play, branch `track-c-trs-integration` from the
    same post-pre-sprint `main` and keep it non-blocking to the live
    smoke path.
-   Use short-lived feature branches under each track, named like
    `track-a/[task-id]` or `track-b/[task-id]`, and merge them back into
    the track branch by PR.
-   Treat `docs/CONTRACT.md` as the day-zero source of truth for mocks,
    shared types, auth conventions, pagination, and trust-envelope
    fields.
-   Aim to sync at at least the three defined points: pre-sprint
    contract committed to `main`, mid-sprint trust-envelope schema
    finalized, and the final joint mock-to-live swap session.
-   If Track C is active, add one early contract-diff review before
    Engineer A finalizes A-7 and Engineer B hardens long-lived shared
    types or fixtures.

## First Steps

1.  Open `docs/workplan/PRE_SPRINT.md` and execute the pre-sprint
    sequence together.
2.  Read `docs/CONTRACT.md`, `docs/workplan/PLAN_BACKEND_PHASE1.md`, and
    `docs/workplan/PLAN_FRONTEND_PHASE1.md` before branching. If using
    Track C, read `docs/workplan/PLAN_TRS_INTEGRATION.md` as well.
3.  After branching, Engineer A starts with Backend Phase 1 Task A-1 and
    Engineer B starts with Frontend Phase 1 Task B-1. If assigned,
    Engineer C starts with TRS Task C-1.
