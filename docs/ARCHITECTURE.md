# Architecture

## Purpose
This repository contains the v1 Image Tagger product boundary: a FastAPI
backend, a React multi-app frontend, shared canonical docs, and deployment
assets needed to support Explorer, Workbench, Monitor, and Admin.

## Repo Boundary
The canonical repo root is organized around `backend/`, `frontend/`, `docs/`,
`deploy/`, and `_archive/`. Historical release material, sibling projects,
legacy changelogs, exploratory scraping, and mined source docs live only under
`_archive/` and are not execution authority for v1.

## Backend
`backend/` contains the FastAPI application, versioned routers, service layer,
SQLAlchemy models, schemas, database utilities, scripts, tests, and the science
pipeline. The science stack includes deterministic CV and math analyzers, room
detection, optional materials enrichment hooks, canonical run tracking, and
structured artifacts surfaced to the product through API responses.

## Frontend
`frontend/` is a React monorepo with four apps under `frontend/apps/`:
`explorer`, `workbench`, `monitor`, and `admin`. Shared UI, API-client, and
cross-app utilities belong in the frontend workspace rather than in the
individual journey apps.

## Shared Contracts
`docs/CONTRACT.md` is the source of truth for v1 endpoint shapes, auth rules,
error envelopes, upload policy, post-upload processing semantics, shared types,
and ML trust-envelope fields. Track work must update the contract first when a
cross-stack schema changes.

## Deployment Surface
`deploy/` holds the Docker, compose, and host-facing deployment assets. The
runtime topology remains a frontend plus backend stack with supporting storage
and database services, and the repo root `.github/workflows/` directory is the
canonical CI boundary after the pre-sprint promotion.

## Out-of-Scope Archived Material
Anything under `_archive/` is historical or upstream reference material only,
including the previous archive tree, TRS source snapshots, the biophilia
project, old changelogs, and mined root-level documents. These assets may be
consulted for context, but they do not override current implementation or the
canonical docs under `docs/`.
