# Coordination Plan, Plain-Language Version

| Term | Plain meaning |
|---|---|
| Seam | The boundary where two parts of the project meet. |
| Backend | The Python app that stores data, checks permissions, runs image analysis, and answers browser requests. |
| Frontend | The browser apps that users see and click. |
| Branch | A separate Git line of work. |
| Pull request | A proposed set of Git changes for review before merging. |
| Contract | The written agreement for API addresses, data shapes, permissions, and shared fields. |
| Smoke path | The shortest set of deployed user actions that must work for v1. |
| TRS | Tagging Registry System, an optional source of tag and attribute definitions. |
| Build-time | During setup or generation before the app runs for users. |
| Runtime | While the deployed app is running for users. |
| Supabase Auth | The sign-in service used to create and verify user tokens. |
| Supabase Storage | The file-storage service used for image files. |
| PostgreSQL | The database system used by the hosted backend. |
| Render | The hosting service planned for the Python API. |
| Vercel | The hosting service planned for the browser site. |

# Project Boundary Summary

The Python files and browser files are mostly separated correctly:

- Python code lives under `backend/`.
- Browser code lives under `frontend/apps/` and `frontend/shared/`.

The main risk is the repo root. It previously contained active code, old archives, sibling projects, many changelogs, and other materials in the same top-level space. That makes it hard for two engineers to know where new work belongs.

The recommended approach is a one-day pre-sprint that only cleans the boundary and commits the current docs. Feature work starts after that.

# Coordination Map

This file is required for v1 planning. Coordination Tasks C-1, C-1.5, and C-2 support the final smoke test and are not optional background.

If the team enables the optional TRS track, `docs/workplan/PLAN_TRS_INTEGRATION.md` becomes Engineer C's plan. TRS still must not block the Phase 1 smoke path.

| Sync point | Engineer A backend deliverable | Engineer B frontend dependency |
|---|---|---|
| Pre-sprint | `docs/CONTRACT.md` and phase plans are committed to `main`. | Frontend uses the contract for fake data and shared types. |
| Mid-sprint | Trust-envelope shape is final in the Python schemas. | Browser trust badges and science rows use exactly those fields and status values. |
| End of sprint | Backend deployment and smoke runbook are ready. | Browser switches from fake data to live API calls and runs the smoke test. |

Use these three sync points. Optional Phase 2 work starts only after the v1 milestone is accepted.

## Optional TRS Track

If Engineer C is assigned, TRS starts from the same post-pre-sprint `main` branch.

TRS deliverables are generated local files, validation checks, and proposed contract differences. TRS must not:

- add a required fourth smoke-test dependency
- make the TRS API or UI part of the deployed app
- override `docs/CONTRACT.md` without explicit review

## Branching Strategy

- Engineer A works on `track-a-backend-phase1`.
- Engineer B works on `track-b-frontend-phase1`.
- Engineer C, if assigned, works on `track-c-trs-integration`.
- Use short-lived feature branches under each track branch, such as `track-a/auth-supabase` or `track-b/workbench-form`.
- Open pull requests back into the relevant track branch.

Review focus:

- Engineer A reviews Engineer B's work for contract correctness, not visual styling.
- Engineer B reviews Engineer A's work for API shape correctness, not database internals.
- Engineer C's work is reviewed by Engineer A for backend adoption and by Engineer B when shared labels or types are affected.

Merge order:

1. Backend Phase 1 to `main`.
2. Joint mock-to-live swap.
3. Frontend Phase 1 to `main`.
4. Tag the v1 release.
5. Merge TRS when ready, as long as it does not block the smoke path.

## Optional Coordination Task C-0: TRS Contract-Diff Review

Goal: show TRS-related contract differences early.

Owner: Engineer C proposes; Engineers A and B review.

Files: `docs/TRS_CONTRACT_DIFF.md`, and `docs/CONTRACT.md` only if a change is approved.

Instructions:

- Compare the pinned TRS snapshot with the current image-tagger contract.
- List only changes that could help Phase 1.
- Mark each difference as accepted now, deferred until after v1, or rejected for v1.
- Do this before Engineer A finalizes A-7 and before Engineer B treats shared browser types or fixtures as final.

Done when the reviewed diff file exists and no generated TRS artifact changes the live app contract without approval.

## Coordination Task C-1: Deployed Smoke Test Runbook

Goal: create one shared smoke-test checklist before the final mock-to-live session.

File: `docs/SMOKE_TEST.md`.

Instructions:

- Include exact commands or URLs for checking the deployed API health, opening Explorer, uploading one image as admin, submitting one label as tagger, checking trust badges, and opening Monitor as supervisor.
- Use placeholder environment variables for deployed URLs and JWTs.
- State that Monitor may show either a filled IRR table or the empty state for `{ rows: [] }`.
- Do not require manual SQL or an uncommitted seed path.

Done when `docs/SMOKE_TEST.md` has at least six numbered steps and a final expected outcome.

## Coordination Task C-1.5: Platform Provisioning Checklist

Goal: separate human-owned hosting setup from repo-owned code changes.

Owners:

- Engineer A owns backend platform verification.
- Engineer B owns frontend platform verification.

File: `docs/SMOKE_TEST.md`.

Instructions:

- Name required live services: Render Web Service, Render PostgreSQL, Vercel project, Render and Vercel environment variables, Supabase Auth, and Supabase Storage.
- Make clear which setup must be checked by a human.

Done when the smoke test doc has a prerequisites section with human owners.

## Coordination Task C-2: JWT Provisioning for Smoke Roles

Goal: provide short-lived tokens for protected smoke-test journeys without committing secrets.

Owner: Engineer A.

File: `docs/SMOKE_TEST.md`.

Instructions:

- Create one Supabase Auth test user for each role: `admin`, `tagger`, and `supervisor`.
- Each JWT must include the top-level `role` claim.
- Store test-account credentials in the team password manager.
- Export fresh tokens locally as `SMOKE_ADMIN_JWT`, `SMOKE_TAGGER_JWT`, and `SMOKE_SUPERVISOR_JWT`.
- Never commit JWTs, passwords, or refresh tokens.

Done when the smoke test doc names Engineer A as token owner, lists the three environment variable names, and says raw secrets must not be stored in the repo.

## Joint Phase 1 Task

Task B-9 is done by both engineers together. Use `docs/SMOKE_TEST.md` as the single checklist.

Start B-9 only after:

- Engineer A finishes backend live verification.
- Engineer B finishes frontend live verification.

For Monitor, Phase 1 passes if the deployed API and browser page handle the agreed response shape, including `{ rows: [] }`.
