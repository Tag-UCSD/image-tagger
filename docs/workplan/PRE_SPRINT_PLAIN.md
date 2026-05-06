# Pre-Sprint Plan, Plain-Language Version

| Term | Plain meaning |
|---|---|
| Pre-sprint | One setup day before feature work starts. |
| Repository | The project folder stored in Git. |
| Repo root | The top folder of the project. |
| Branch | A separate Git line of work. |
| Main | The main Git branch that represents the shared current version. |
| Contract | The written agreement for API addresses, data shapes, permissions, and shared fields. |
| Backend | The Python app that stores data, checks permissions, runs image analysis, and answers browser requests. |
| Frontend | The browser apps that users see and click. |
| Archive | Old files kept for reference, not current instructions. |
| Environment variable | A setting passed to a program from the computer or hosting service. |
| Docker | A tool for packaging an app so it runs the same way on a server. |
| TypeScript | The JavaScript-based type system used by the browser code. |
| Pydantic | The Python package used to define and check data shapes. |

**Target duration:** one full working day, about 6 to 8 hours.

## Purpose

This is a setup phase. Do not build product features here.

The goal is to:

- make the project boundary clear
- commit the shared contract
- clean up the top-level docs
- create a stable starting point for Backend Phase 1 and Frontend Phase 1

## Do Not Do These During Pre-Sprint

- Do not verify every developer laptop setup.
- Do not move real production secrets.
- Do not debug runtime problems unless they are caused by the folder move.
- Do not start feature work for either track.

## Target Folder Structure

```text
/
├── backend/                  Python API application
├── frontend/                 browser apps and shared browser code
├── docs/                     current documentation
├── deploy/                   deployment files
├── .github/workflows/        GitHub automation
├── _archive/                 old or out-of-scope material
├── .env.example              setting names with no secret values
├── .gitignore
└── README.md                 short pointer to main docs
```

`docs/workplan/` stays current. It is not archive material.

## Shared Contract Reference

Use `docs/CONTRACT.md` as the only source of truth for:

- v1 API endpoint shapes and examples
- permission rules and error response shape
- shared TypeScript and Pydantic types
- machine-learning trust fields
- Workbench assignment fields
- pagination limits
- upload validation rules
- post-upload processing behavior
- environment variable names

If the contract changes, update `docs/CONTRACT.md`. Do not copy contract details into this file.

## Folder Move Rules

When moving the active project to the repo root, follow these rules instead of deciding case by case:

| Path | What to do | How to check |
|---|---|---|
| `docs/` | Keep the current outer `docs/` as the current docs. Preserve old inner docs under `_archive/`. | `docs/CONTRACT.md`, `docs/ENGINEERING_BRIEF.md`, `docs/SMOKE_TEST.md`, and `docs/workplan/PRE_SPRINT.md` exist. |
| `.github/` | Move the active project `.github/` directory to the repo root. | `.github/workflows` exists. |
| `README*` | Move useful active-project README material, then rewrite root `README.md` as a short pointer doc. | Root README exists and points to the main docs. |
| `.gitignore` | Keep the outer `.gitignore` unless a later change deliberately adds missing rules. | `.gitignore` exists and includes needed root ignores. |
| `.DS_Store` | Delete these generated files. | `find . -name '.DS_Store'` returns no matches. |
| `.pytest_cache/` | Delete these generated cache folders. | `find . -name '.pytest_cache' -type d` returns no matches. |

## Pre-Sprint Sequence

### Phase 1: Establish the Project Boundary

- [ ] Create `_archive/` at the repo root. Move old archives, scraping files, old changelogs, helper scripts, and sibling projects into it. Done when no old active-looking folders remain at the top level outside `_archive/`.
- [ ] Move the active project contents to the repo root. Follow the folder move rules above. Done when `backend/main.py`, `frontend/package.json`, `deploy/`, and `.github/workflows/` exist at the repo root.
- [ ] Update Python import paths and project references that assumed the old nested folder. Done when `python -c "import backend.main"` works from the repo root.

### Phase 2: Create Current Docs

- [ ] Commit `docs/CONTRACT.md` as the current source of truth. Done when the file is committed on `main`.
- [ ] Create `docs/ARCHITECTURE.md` with the required headings and keep it short. Done when it exists, has the required headings, and is 120 lines or fewer.
- [ ] Rewrite root `README.md` as a short pointer to `docs/ARCHITECTURE.md`, `docs/CONTRACT.md`, and the workplan docs. Done when it is 20 lines or fewer and links to those docs.

### Phase 3: Prepare Branches

- [ ] Review the folder structure, contract, and branch plan together. Done when the merge message or pull request description names the current paths for `backend/`, `frontend/`, `docs/`, `deploy/`, and `_archive/`.
- [ ] Create `track-a-backend-phase1` and `track-b-frontend-phase1` from the post-pre-sprint `main`. Done when both branches exist locally and remotely.

## Deferred To Sprint Tasks

These are not pre-sprint tasks:

- moving secrets to environment variables
- creating the full `.env.example`
- cleaning up Docker credentials
- checking each laptop setup

## Exit Criteria

Do not start track work until all of these are true:

1. `main` contains the pre-sprint merge commit and both engineers have pulled it.
2. `docs/CONTRACT.md` exists on `main` and both engineers have read it.
3. `docs/ARCHITECTURE.md` exists and root `README.md` points to it and the contract.
4. The repo root has no stray changelogs, no sibling projects, and no `archive/` folder outside `_archive/`.
5. `track-a-backend-phase1` and `track-b-frontend-phase1` exist and both started from the post-pre-sprint `main`.
