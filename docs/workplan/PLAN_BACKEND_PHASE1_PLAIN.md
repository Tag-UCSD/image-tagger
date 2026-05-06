# Backend Phase 1, Plain-Language Version

| Term | Plain meaning |
|---|---|
| Backend | The Python app that stores data, checks permissions, runs image analysis, and answers browser requests. |
| Endpoint | One API web address, such as `/health`. |
| Environment variable | A setting passed to the app from the computer or hosting service. |
| Secret | A password, token, private key, or other value that must not be committed to Git. |
| JWT | A signed text token that says who a user is and what role they have. |
| Middleware | Python code that runs before or after each API request. |
| Structured log | A log written as fields, often JSON, instead of free-form text. |
| Pydantic | The Python package used to define and check data shapes. |
| Integration test | A test that checks multiple parts of the app working together. |
| Trust envelope | Extra fields attached to a model result that explain how well-supported that result is. |
| Render | The hosting service planned for the Python API. |
| Supabase Auth | The sign-in service used to create and verify user tokens. |
| Docker | A tool for packaging an app so it runs the same way on a server. |
| SQLite | A small database that can run inside tests. |

**Owner:** Engineer A.

**Scope:** files under `backend/`, `deploy/`, and deployment-related docs needed for v1.

**Out of scope:** browser code under `frontend/`, formal model-evaluation reports, and optional hardening that does not block v1.

`docs/workplan/COORDINATION.md` is required for this track. Tasks C-1, C-1.5, and C-2 are required support work for Phase 1.

## Phase 1 End State

Backend Phase 1 is complete when:

- protected API endpoints require valid bearer JWTs
- all v1 endpoints validate input and return standard error objects
- the Python app writes request-level structured logs
- machine-learning outputs use the trust-envelope format
- unproven model results are marked `untested`
- integration tests cover the smoke-test paths for Explorer, Workbench, Admin, and Monitor
- the backend can be deployed from committed configuration
- the backend-owned smoke-test steps pass

Phase 1 does not claim:

- formal statistical proof for machine-learning models
- upgraded `validated` model status without evidence
- production-grade abuse protection beyond basic auth and validation
- Prometheus metrics, which are numeric monitoring data for production systems
- full Alembic migration replacement, which is a complete replacement of database change scripts using the Python package `alembic`
- Sentry production error recording
- GitHub deploy automation
- a monitor seed workflow
- broad test hardening

## Task A-1: Environment and Secrets Management

Goal: remove hardcoded secrets and stop clearly when required configuration is missing.

Files: `backend/settings.py`, `backend/main.py`, `deploy/docker-compose.yml`, `.env.example`.

Instructions:

- Use the Python package `pydantic-settings`.
- Use the environment variable list in `docs/CONTRACT.md` as the starting list for `.env.example`.
- Add any backend-only setting names discovered while implementing.
- Define typed settings for `database_url`, `supabase_jwt_secret`, `cors_allowed_origins`, and `vlm_hard_limit_usd`.
- Require production-critical settings in production.
- Allow development defaults only when `ENVIRONMENT=development`.
- In `backend/main.py`, raise a clear `RuntimeError` during startup if a required production setting is missing.
- Remove all fallback secrets such as `"dev_secret_key_change_me"`.

Done when production startup fails clearly if `SUPABASE_JWT_SECRET` is missing, secret placeholders are gone, and local startup works after creating `.env` from `.env.example`.

## Task A-2: Structured Logging and Request Middleware

Goal: replace scattered debugging output with JSON request logs.

Files: `backend/logging_config.py`, `backend/middleware/request_context.py`, `backend/main.py`, `backend/services/auth.py`.

Instructions:

- Use the Python package `structlog`.
- Generate a `request_id` for each request.
- Return the request ID in the `X-Request-ID` response header.
- Log one JSON line per request with method, path, status, duration in milliseconds, user ID, and role.
- Use warning logs for failed admin authentication attempts.

Done when `/health` returns `X-Request-ID`, logs are parseable JSON, and `print(` debugging is removed from backend API and service files.

## Task A-3: Authentication With Supabase Auth

Goal: verify signed JWTs instead of trusting browser-supplied role text.

Files: `backend/services/auth.py`, `backend/tests/test_auth.py`.

Instructions:

- Use the Python package `python-jose` to verify Supabase JWTs signed with HS256.
- Read the signing secret from `SUPABASE_JWT_SECRET`.
- Read user ID from JWT claim `sub`.
- Read role from top-level JWT claim `role`.
- Provide dependency functions for the Python package `fastapi` for tagger, scientist, supervisor, and admin access.
- Keep Explorer public.
- Return `401` when a protected endpoint has no valid bearer token.
- Return `403` when the token is valid but the role is not allowed.
- Keep any local bypass token available only in `ENVIRONMENT=development`.

Done when tests prove a valid admin token works, a tampered token fails with `401`, and a tagger token cannot access admin budget.

## Task A-4: Input Validation and Error Handling

Goal: every endpoint checks input and returns the same error shape.

Files: API route files under `backend/api/`, schema files under `backend/schemas/`, and `backend/main.py`.

Instructions:

- Use the Python package `pydantic` to define query, body, and upload validation.
- Add limits such as `page >= 1`, maximum text lengths, and upload batch sizes.
- Add exception handlers in `backend/main.py`.
- Return the `ErrorResponse` shape from `docs/CONTRACT.md` for all non-success responses.
- Use `code: "VALIDATION_ERROR"` and `message: "Request validation failed"` for validation failures.
- Log unexpected errors with stack traces.
- Roll back database writes explicitly when a mutating operation fails.
- Remove runtime clamping when a schema already handles the rule.

Done when invalid Explorer and Admin upload requests return the standard error object, database errors include request IDs, and mutating database paths roll back on failure.

## Task A-7: Machine-Learning Trust Envelope

Goal: every machine-learning output states its trust status.

Files: `backend/science/trust.py`, `backend/science/pipeline.py`, `backend/science/features_registry.py`, `backend/schemas/science.py`, `backend/tests/test_science_schema.py`.

Instructions:

- Define a `TrustEnvelope` model with the Python package `pydantic`, matching the contract.
- Mark each feature as `validated`, `proxy_validated`, or `untested`.
- Wrap every feature output inside `SciencePayload.features`.
- Do not create a separate feature confidence map.
- Default old features without metadata to `untested`.
- Test this with controlled test data, not by depending on a live image.

Done when tests prove every feature has the required trust fields, missing trust status fails validation, and at least one old feature is returned as `untested`.

## Task A-10: Health Check and Basic Observability

Goal: `/health` checks real dependencies.

Files: `backend/api/health.py`, `backend/main.py`.

Instructions:

- `/health` must run `SELECT 1` against the database.
- It must check that `IMAGE_STORAGE_ROOT` is writable.
- It must return `status`, `db`, `storage`, and `version`.
- Do not add Prometheus metrics in Phase 1.
- Do not add Sentry in Phase 1.

Done when `/health` returns success while dependencies work, returns degraded or unavailable when the database is stopped, and no Phase 1 metrics code is added.

## Task A-11: Smoke-Critical Integration Tests

Goal: test the deployed smoke-test paths without trying to test every endpoint.

Files: backend integration tests and backend test workflow.

Instructions:

- Use the Python package `pytest`.
- Use the Python package `httpx`.
- Use an in-memory SQLite test database for each test where possible.
- Create test JWTs using the same secret the app uses in test mode.
- Test anonymous Explorer search/detail.
- Test protected Workbench next/validate.
- Test Admin upload, budget, and kill-switch permission behavior.
- Test Monitor velocity and IRR shape, including `{ rows: [] }`.
- Test shared validation and auth error shapes.
- Add a GitHub workflow with a concrete `pytest` command for these tests.
- Do not add BN export tests; BN export is not in the v1 contract.

Done when the smoke-critical integration test command passes and the workflow runs those tests without enforcing a Phase 1 coverage threshold.

## Task A-12a: Backend Deployment Repo Configuration

Goal: make the Python API deployable to Render from committed files.

Files: `render.yaml`, `deploy/Dockerfile.backend`, `docs/SMOKE_TEST.md`.

Instructions:

- Use Render Web Service and Render PostgreSQL in repo configuration.
- Start the server with the Python package `uvicorn`.
- Run as a non-root user in the Docker image.
- Use Supabase Storage for image storage, not Render's temporary disk.
- Create the smoke-test runbook with placeholder environment variables.
- Make Engineer A the owner of JWT provisioning for smoke-test roles.
- Never write raw tokens or passwords in the runbook.
- State the async upload rules: upload returns queued work, image detail is reachable within 5 seconds, and science completes within 60 seconds for the smoke-test image.

Done when deployment files and `docs/SMOKE_TEST.md` exist, the runbook names the smoke JWT variables, and no deferred Phase 2 tools are required for Phase 1 deployment.

## Task A-12b: Backend Platform Provisioning and Live Verification

Goal: have a human verify the real hosted backend.

Human prerequisites:

- Render Web Service linked to the repo
- Render PostgreSQL instance
- required backend secrets and environment variables in Render or GitHub
- Supabase project with Auth and Storage configured
- fresh role JWTs for admin, tagger, and supervisor

Instructions:

- Do not hand this task to an agent as if repo files alone can prove it.
- Use the configuration from A-12a and real platform accounts.
- If live verification finds a repo defect, fix it in a follow-up commit.

Done when a human deploys the backend, `/health` returns `200` with `db: true`, admin upload works, the uploaded image becomes reachable, science completes within 60 seconds, Workbench validation succeeds, and Monitor returns the agreed shape if data exists.
