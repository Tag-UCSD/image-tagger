# Backend Phase 2, Plain-Language Version

| Term | Plain meaning |
|---|---|
| Backend | The Python app that stores data, checks permissions, runs image analysis, and answers browser requests. |
| Phase 2 | Optional follow-up after v1 already works. |
| Rate limit | A rule that blocks too many requests in a short time. |
| Observability | Tools and logs that help diagnose problems in the deployed app. |
| Sentry | A service for recording production errors. |
| Seed data | Test data inserted so a feature can be checked predictably. |
| IRR | Inter-rater reliability: a measure of how consistently different labelers agree. |
| CI | GitHub automation that runs checks when code changes. |
| LightGBM | A machine-learning package used by some model files. |
| Confidence interval | A range that estimates uncertainty around a metric. |
| Redis | A database often used to share fast counters across multiple app servers. |
| Render | The hosting service planned for the Python API. |

**Owner:** Engineer A.

**Scope:** optional backend hardening and evidence-generation work after v1 is already usable.

**Out of scope:** any work required to make the v1 smoke test pass.

## Phase 2 End State

Backend Phase 2 is complete when:

- expensive or sensitive endpoints have rate limits
- deployed error capture exists
- backend deployment automation is committed and checked
- monitor smoke-test data can be prepared with a script
- model trust statuses are upgraded only when evidence supports them
- `docs/ML_EVALUATION.md` contains real evaluation results

Phase 2 must not block the v1 tag.

## Task A-10.5: Sentry Integration

Goal: record deployed errors without changing API responses.

Files: `backend/main.py`, `backend/logging_config.py`, and deployment config if needed.

Instructions:

- Use the Python package `sentry-sdk` with support for the Python package `fastapi`.
- Enable Sentry only when `SENTRY_DSN` is set.
- Keep local development quiet.
- Keep structured logs as the main local debugging path.

Done when the app behaves the same with `SENTRY_DSN` unset, and a deliberate deployed error appears in Sentry with request path and request ID.

## Task A-11.5: Seed Monitor Smoke Dataset

Goal: create repeatable data for the deployed Monitor IRR check.

Files: `backend/scripts/seed_monitor_smoke.py`, `backend/tests/integration/test_monitor.py`, `docs/SMOKE_TEST.md`.

Instructions:

- Write one explicit seed script instead of typing manual SQL during the smoke test.
- Create at least 10 overlapping validations for one known `attribute_key`.
- Use two different tagger identities across 10 different images.
- Document the seed command and a verification command in `docs/SMOKE_TEST.md`.

Done when the seed command creates the data, verification confirms it, `GET /v1/monitor/irr` returns at least one row with `n_pairs >= 10`, and tests cover the seeded case.

## Task A-12c: GitHub Deploy Automation

Goal: add automated backend deployment after manual Render deployment is stable.

Files: `.github/workflows/deploy_backend.yml`, and `docs/SMOKE_TEST.md` if deployment steps change.

Instructions:

- Add automation only after the Phase 1 manual deployment path works.
- Limit the workflow to backend-facing changes.
- Make deployment failures distinguishable from application bugs.

Done when the workflow exists, is scoped to backend/deploy changes, and one human push triggers a successful backend deploy.

## Task A-5: Rate Limiting

Goal: limit request rates for expensive and permission-sensitive endpoints.

Files: `backend/middleware/ratelimit.py`, `backend/main.py`.

Instructions:

- Add this only after auth, errors, and deployment are stable.
- Use the Python package `slowapi`.
- Use these limits:
  - `/v1/admin/upload`: 20 per hour per user
  - `/v1/workbench/validate`: 600 per hour per user
  - all `/v1/admin/*`: 200 per hour per user
  - unauthenticated Explorer endpoints: 60 per minute per IP address
- Use in-memory storage for the single-instance deploy.
- Leave a code comment explaining how to move to Redis later.

Done when a test that sends 25 upload requests quickly gets at least five `429` responses.

## Task A-8: Statistical Validation for Affordance Models

Goal: evaluate the LightGBM affordance models and document the evidence.

Files: `backend/science/evaluation/affordance_eval.py`, `docs/ML_EVALUATION.md`, and evaluation report JSON files under `backend/science/data/affordance_models/`.

Instructions:

- Load each model from its existing `.pkl` file.
- Rebuild a held-out test set only if the available manual labels are sufficient and trustworthy.
- Compute R-squared, MAE, and Pearson correlation.
- Use bootstrap confidence intervals.
- If data is insufficient, keep the model marked `untested` and explain why.
- Do not invent evidence to satisfy the plan.

Done when `docs/ML_EVALUATION.md` has one section per model with sample size, estimates, 95% confidence intervals, and a verdict, and runtime trust envelopes match those verdicts.

## Task A-9: Validation for Segmentation and Room Detection

Goal: evaluate image segmentation and room detection against a curated test set.

Files: `backend/science/evaluation/vision_eval.py`, `backend/science/evaluation/test_sets/rooms.csv`, `docs/ML_EVALUATION.md`.

Instructions:

- First agree on what counts as trusted test data and who labels it.
- For room detection, compute top-1 accuracy, top-3 accuracy, and a confusion matrix.
- For segmentation, use mean IoU on images with manual region polygons.
- Report uncertainty intervals.
- Keep outputs marked `untested` where evidence is weak.

Done when `docs/ML_EVALUATION.md` contains sample sizes, metrics, intervals, and verdicts, and any runtime `validated` status is backed by documented evidence.
