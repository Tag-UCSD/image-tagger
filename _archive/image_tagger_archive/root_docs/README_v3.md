# Image Tagger v3.4.74

Image Tagger is a multi-app research system for architectural and interior-image
annotation, science feature extraction, and downstream exploratory analysis.

The current `3.4.74` line includes a versioned canonical science pipeline with
explicit run tracking, structured artifacts, and Explorer-facing status APIs.

## Architecture

- Frontend: React monorepo with 4 SPAs under `frontend/apps/`
  - `workbench`
  - `monitor`
  - `admin`
  - `explorer`
- Backend: FastAPI + SQLAlchemy + PostgreSQL
- Gateway: Docker Compose + Nginx frontend container
- Science stack:
  - deterministic CV/math analyzers
  - Places365 room detection
  - optional materials enrichers
  - canonical science-run persistence

## Canonical science pipeline

The current science system is centered on:

- `backend/science/pipeline.py`
- `backend/services/science_runs.py`
- `backend/models/science_runs.py`

Key behavior:

- Explorer bootstraps canonical processing with
  `POST /api/v1/explorer/science/bootstrap`
- Progress is reported by `GET /api/v1/explorer/science/status`
- Each run is versioned and fingerprinted
- Canonical tags are stored in `science_tags`
- Structured outputs are stored in `science_artifacts`
- Numeric science attributes are still persisted to `Validation`

The active version is defined in code and is currently the `3.4.74` canonical
line.

Current default canonical outputs:

- deterministic science attributes
- room detection attributes plus `room_json`
- material heuristic summaries when available

Current known runtime gaps:

- affordance inference is implemented but currently affected by a LightGBM model
  compatibility problem in this environment
- segmentation exists in the codebase but is disabled in the default canonical
  config, so segmentation/object artifacts are not currently part of the default
  production path

## Quick start

From the app root:

```bash
./install.sh
docker-compose -f deploy/docker-compose.yml up -d
```

Primary URLs:

- Explorer: `http://localhost:8080/explorer`
- Workbench: `http://localhost:8080/workbench`
- Monitor: `http://localhost:8080/monitor`
- Admin: `http://localhost:8080/admin`
- API docs: `http://localhost:8080/api/docs`

## Backfill operations

For bulk science processing beyond the Explorer bootstrap queue, use:

```bash
python backend/scripts/backfill_science_runs.py --status
python backend/scripts/backfill_science_runs.py --batch 50 --limit 1000
python backend/scripts/backfill_science_runs.py --id-range 100 200
python backend/scripts/backfill_science_runs.py --retry-failed
```

This script runs the same canonical pipeline in-process and is the preferred
operator tool for large backfills.

## Testing

Useful current tests:

- `pytest tests/test_v3_api.py -v`
- `pytest tests/test_explorer_smoke.py -v`
- `pytest tests/test_tag_derivation.py -v`
- `pytest tests/test_science_runs.py -v`

The last two are the targeted tests for the new canonical science-run path.

## Documentation map

- `docs/science_overview.md` for the current science architecture
- `docs/SCIENCE_TAG_MAP.md` for canonical tag coverage
- `docs/ops/Technical_Lead_Runbook_v3.4.74.md` for operator workflow
- `docs/AI_COLLAB_WORKFLOW.md` for repo collaboration and governance expectations
- `docs/PRODUCTION_DEPLOYMENT.md` for deployment concerns

## Notes

This repository still contains older docs and archived release material. When
there is a conflict, prefer:

1. the current implementation in `backend/` and `frontend/`
2. the canonical-science docs listed above
3. archived or historical documentation only for context
