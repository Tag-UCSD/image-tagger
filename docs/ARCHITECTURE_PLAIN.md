# Architecture, Plain-Language Version

| Term | Plain meaning |
|---|---|
| Repository | The project folder stored in Git. |
| Repo root | The top folder of this project. |
| Backend | The Python program that stores data, checks permissions, runs image analysis, and answers requests from the user-facing pages. |
| Frontend | The browser pages that people see and click. |
| API | A set of web addresses that one program uses to ask another program for data or actions. |
| Contract | The written agreement for what each API address accepts and returns. |
| Deployment | Putting the project on internet services so other people can use it. |
| Archive | Old files kept for reference, not for current instructions. |

## Purpose

This repository contains the v1 Image Tagger product. The product lets people browse images, label images, review labeling quality, and manage uploads.

The project has:

- a Python application built with the Python package `fastapi`
- browser apps built with the JavaScript package `react`
- shared documentation
- deployment files
- old material stored in `_archive/`

## Repository Boundary

The current project is organized around these folders:

- `backend/`: Python code for data storage, permissions, image analysis, and API responses
- `frontend/`: browser code for the four user journeys
- `docs/`: current planning and contract documents
- `deploy/`: files used when running the app on a hosting service
- `_archive/`: old or reference material

Use the documents in `docs/` for current work. Do not treat files in `_archive/` as current instructions unless a plan explicitly says to use a specific archived source.

## Backend

`backend/` contains the Python application. It includes:

- API route files, which define the web addresses the browser can call
- service files, which contain the main application logic
- database model files, which describe stored data
- schema files, which describe valid request and response shapes
- database helper files
- scripts
- tests
- image-analysis code under `backend/science/`

The image-analysis code creates structured outputs that the product can display. Those outputs must also include information about how much trust users should place in them.

## Frontend

`frontend/` contains the browser apps. The four apps are:

- Explorer: public browsing and image detail
- Workbench: labeling assigned images
- Monitor: supervisor review
- Admin: uploads, budget display, and a kill switch

Shared browser code, shared display components, and the shared API client belong in the shared frontend workspace, not copied separately into each app.

## Shared Contracts

`docs/CONTRACT.md` is the source of truth for:

- API web addresses
- required permissions
- error response shape
- upload rules
- image-analysis trust fields
- shared data types
- environment variable names

If a change affects both the Python application and the browser apps, update the contract first.

## Deployment Surface

`deploy/` contains files used to run the project on hosting services. The expected v1 deployment has:

- one browser site
- one Python API service
- a database
- image storage

The `.github/workflows/` folder at the repo root is where GitHub automation files belong.

## Out-of-Scope Archived Material

Anything under `_archive/` is historical or reference material. This includes old project snapshots, the TRS source snapshot, the biophilia project, old changelogs, and collected source documents.

You may read archived files for context, but they do not override current implementation plans or the current docs under `docs/`.
