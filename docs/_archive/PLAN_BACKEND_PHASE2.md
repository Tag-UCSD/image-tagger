# BACKEND PHASE 2

**Owner:** Engineer A. **Scope:** optional hardening and evidence-generation work that improves credibility after v1 is already usable. **Out of scope:** any work required to make the v1 smoke flow function.

## Phase 2 End State

Phase 2 is complete when:

- expensive or sensitive endpoints have explicit rate limits
- backend observability includes production error capture
- deployment automation from GitHub to the backend platform is committed and verified
- monitor smoke preparation is reproducible from a dedicated seed path
- ML trust statuses are upgraded based on documented evidence rather than defaults
- `docs/ML_EVALUATION.md` contains real evaluation artifacts and verdicts

Phase 2 must not block the v1 tag. If time runs out, Phase 1 is still the shipped portfolio milestone.

## Task List

#### Task A-10.5: Sentry Integration
- **Goal:** Add production error capture without changing the contracted API surface.
- **Files to create or modify:** `backend/main.py`, `backend/logging_config.py`, deploy-facing config files if needed.
- **Implementation notes:** Integrate Sentry SDK (`sentry-sdk[fastapi]`) gated on `SENTRY_DSN` being set. Keep local development noise low and do not change structured log output as the primary local debugging path.
- **Acceptance criteria:** With `SENTRY_DSN` unset, the app starts and behaves exactly as in Phase 1; with `SENTRY_DSN` set in a non-local environment, one deliberate unhandled exception is captured in Sentry with the request path and request id present in the event context.
- **Depends on:** A-10 from Phase 1.

#### Task A-11.5: Seed Monitor Smoke Dataset
- **Goal:** Create the reproducible paired-validation dataset required for the deployed monitor IRR smoke step.
- **Files to create or modify:** `backend/scripts/seed_monitor_smoke.py` (new), `backend/tests/integration/test_monitor.py`, `docs/SMOKE_TEST.md`.
- **Implementation notes:** Engineer A owns this task. Implement one explicit seed path rather than manual database edits. The seed script must create at least 10 overlapping validations for one known `attribute_key`, produced by two distinct tagger identities across 10 distinct images, so the deployed `GET /v1/monitor/irr` contract can return at least one row with `n_pairs >= 10`. The script may assume an existing database plus the auth/user model established in Phase 1, but it must not require ad hoc SQL typed during the smoke session. `docs/SMOKE_TEST.md` must reference the exact seed command and a verification command for the seeded attribute before the joint session begins.
- **Acceptance criteria:** Running the documented seed command creates the paired-validation dataset for one named `attribute_key`; a documented verification command confirms the dataset exists before the smoke session; `GET /v1/monitor/irr` returns at least one row with `n_pairs >= 10` after seeding; `backend/tests/integration/test_monitor.py` includes coverage for the seeded IRR-ready case.
- **Depends on:** A-3, A-4, A-11 from Phase 1.

#### Task A-12c: GitHub Deploy Automation
- **Goal:** Add repository-managed backend deploy automation after the manual Phase 1 deployment path is stable.
- **Files to create or modify:** `.github/workflows/deploy_backend.yml` (new), `docs/SMOKE_TEST.md` if deploy steps change.
- **Implementation notes:** Implement this only after Render deployment via committed config has been proven manually. Scope the workflow to backend-facing changes and make sure failures are distinguishable from application defects.
- **Acceptance criteria:** `test -f .github/workflows/deploy_backend.yml` exits `0`; `rg -n "paths:|backend/|deploy/|render\\.yaml" .github/workflows/deploy_backend.yml` shows backend-facing path scoping; one human push that changes `backend/` triggers the workflow and results in a successful backend deploy.
- **Depends on:** A-12b from Phase 1.

#### Task A-5: Rate Limiting
- **Goal:** Bound request rates per user and per IP on expensive and auth-sensitive endpoints.
- **Files to create or modify:** `backend/middleware/ratelimit.py` (new or adapted reference), `backend/main.py`.
- **Implementation notes:** Implement this only after auth, error handling, and deployment are stable enough that rate-limit failures are easy to distinguish from application bugs. Use `slowapi`. Limits: `/v1/admin/upload` 20/hour per user; `/v1/workbench/validate` 600/hour per user; all `/v1/admin/*` 200/hour per user; unauthenticated explorer endpoints 60/minute per IP. Storage backend is in-memory for single-instance deploy; document the Redis upgrade path in code comments.
- **Acceptance criteria:** An integration test that fires 25 upload requests in one second as the same user receives at least five `429` responses.
- **Depends on:** A-3, A-10, A-11 from Phase 1.

#### Task A-8: ML Model Statistical Validation — Affordance LightGBM Models
- **Goal:** Produce held-out evaluation artifacts for the LightGBM affordance models and document them.
- **Files to create or modify:** `backend/science/evaluation/affordance_eval.py` (new), `docs/ML_EVALUATION.md`, `backend/science/data/affordance_models/L*/evaluation_report.json`.
- **Implementation notes:** Load each model from its existing `.pkl`. Reconstruct a held-out set from available manual validations only if the underlying data is sufficient and provenance is clear. Compute R², MAE, and Pearson r with bootstrap confidence intervals. If the data is insufficient, keep the model `untested` and document why. Phase 2 is where trust statuses may be upgraded from `untested` to `validated` or `proxy_validated`; do not manufacture evidence to satisfy the plan.
- **Acceptance criteria:** `docs/ML_EVALUATION.md` contains one subsection per affordance model with sample size, point estimates, 95% CIs, and a verdict; runtime trust envelopes for the same models reflect the same verdicts.
- **Depends on:** A-7 from Phase 1, plus sufficient labeled-data availability.

#### Task A-9: ML Model Validation — Segmentation and Room Detection
- **Goal:** Validate segmentation and room-detection outputs against a curated test set.
- **Files to create or modify:** `backend/science/evaluation/vision_eval.py` (new), `backend/science/evaluation/test_sets/rooms.csv` (new), `docs/ML_EVALUATION.md`.
- **Implementation notes:** Curate a test set only after agreeing what counts as gold data and who is responsible for labeling it. For room detection, compute top-1 and top-3 accuracy plus a confusion matrix over the dominant classes. For segmentation, use mean IoU on images with manual region polygons. Report uncertainty intervals and leave outputs `untested` where evidence remains weak.
- **Acceptance criteria:** `docs/ML_EVALUATION.md` contains room-detection and segmentation evaluation sections with sample sizes, metrics, intervals, and verdicts; any runtime `validated` status for these outputs is backed by the documented thresholds in the same file.
- **Depends on:** A-7 from Phase 1, plus an agreed evaluation dataset. Does not require A-8 to finish first.
