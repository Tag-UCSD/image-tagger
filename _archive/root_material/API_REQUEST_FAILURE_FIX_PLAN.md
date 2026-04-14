# API Request Failure Remediation Plan

## Goal
Eliminate `"API Request Failed"` errors across Workbench, Explorer, Monitor, and Admin by fixing shared request-path, auth, and client-contract defects.

## Scope
Included:
- Dev proxy path rewrite bug (`/api/v1/...` incorrectly rewritten to `/v1/v1/...`)
- Privileged auth header mismatch (`X-Auth-Token` missing for admin/supervisor calls)
- Monitor inspector request bypassing shared API client/auth behavior
- Missing `ApiClient.patch()` method used by Admin UI
- Hardening of error visibility and diagnostics for faster triage

Excluded:
- API key exposure/remediation

---

## Phase 0: Baseline & Repro Matrix

1. Capture reproducible failures for each app in both modes:
- Vite dev mode (`npm run dev` per app)
- Docker/Nginx mode (`deploy/docker-compose up --build`)

2. Record current failing endpoints and status codes:
- Workbench: `/api/v1/workbench/next`, `/api/v1/workbench/validate`
- Explorer: `/api/v1/explorer/attributes`, `/api/v1/explorer/search`, `/api/v1/explorer/export`
- Monitor: `/api/v1/monitor/velocity`, `/api/v1/monitor/irr`, `/api/v1/debug/pipeline_health`, `/api/v1/monitor/image/{id}/inspector`
- Admin: `/api/v1/admin/*`, `/api/v1/vlm-health/*`

3. Confirm which failures are:
- 404/route misses (proxy rewrite issue)
- 401 auth failures (missing token)
- Runtime UI errors (missing client method)
- 502/infra availability errors

Deliverable:
- Short issue table (app, endpoint, status, root cause bucket).

---

## Phase 1: Fix Request Routing in Dev

Problem:
- Vite proxy rewrites `/api` to `/v1`, producing `/v1/v1/...` for already-versioned URLs.

Changes:
1. Update `frontend/vite.config.base.js`:
- Remove rewrite entirely for `/api`, or
- Rewrite only `/api/` to `/` if needed by legacy routes.
- Keep `/static` proxy unchanged.

2. Verify per-app dev behavior:
- Open each app and inspect network requests.
- Confirm frontend requests remain `/api/v1/...` and backend receives `/v1/...` (via FastAPI prefix stripping where applicable).

Acceptance criteria:
- No `/v1/v1/...` requests in network logs.
- Workbench and Explorer core calls return expected HTTP status (not 404 from bad pathing).

---

## Phase 2: Align Privileged Auth Between Frontend and Backend

Problem:
- Backend enforces `X-Auth-Token` for privileged roles.
- Admin/Monitor clients send role header but not token.

Changes:
1. Standardize frontend auth header injection in `ApiClient`:
- Add optional token source (e.g., `window.__IMAGE_TAGGER_AUTH_TOKEN__` or env variable wiring).
- Include `X-Auth-Token` automatically when present.

2. Update privileged app client construction:
- Admin + Monitor + Debug + VLM health clients should all use shared token flow.
- Replace any direct privileged `fetch(...)` calls with `ApiClient` usage where practical.

3. Environment consistency in deployment:
- Ensure backend reads the same secret configured at runtime (`API_SECRET` expected by auth layer).
- Ensure frontend can receive token in the deployment model (if static frontend, define a secure bootstrap mechanism).

Acceptance criteria:
- Admin and Monitor endpoints return 200 with valid token, 401 without token.
- No privileged endpoint depends on ad-hoc header handling.

---

## Phase 3: Fix Monitor Inspector Path

Problem:
- Inspector drawer uses direct `fetch` without shared auth handling, causing partial Monitor failures.

Changes:
1. Refactor inspector call to use existing monitor `ApiClient` instance.
2. Keep response handling consistent with shared error parser.
3. Validate drawer behavior for:
- Success payload rendering
- 401/403 display
- 404 missing image handling

Acceptance criteria:
- Inspector opens without auth-related failure when user is authorized.
- Inspector errors surface meaningful backend detail (not generic failure text).

---

## Phase 4: Restore API Client Contract Completeness

Problem:
- Admin UI calls `api.patch(...)`, but `ApiClient` lacks `patch()`.

Changes:
1. Add `patch(endpoint, body, options)` in `frontend/shared/src/api-client.js`.
2. Ensure header merge behavior matches `post`/`put`.
3. Validate Admin actions that depend on patch:
- Model enabled toggle
- Model cost update

Acceptance criteria:
- No `api.patch is not a function` runtime errors.
- PATCH requests emit expected payload and succeed against backend.

---

## Phase 5: Error Handling & UX Hardening

Goals:
- Reduce opaque `"API Request Failed: <status>"` cases.
- Make root causes visible to operators and developers.

Changes:
1. Improve non-JSON error parsing:
- Fall back to `response.text()` snippet when JSON parse fails.
- Preserve status and endpoint in surfaced message.

2. Add centralized request diagnostics (dev-only):
- Optional debug logging with method, URL, status, timing.

3. Normalize user-facing error copy:
- Distinguish auth failures (`401/403`), route/config issues (`404`), gateway/backend-down (`502/503`), and server exceptions (`500`).

Acceptance criteria:
- Error banners/toasts identify failure class and endpoint context.
- Faster triage with minimal console digging.

---

## Phase 6: Test Coverage Additions

Backend tests:
1. Auth/RBAC:
- Explicit tests for privileged endpoints requiring `X-Auth-Token`.
- Verify expected 401/403/200 flows.

2. Prefix compatibility:
- Validate `/api/v1/...` and `/v1/...` behavior under middleware settings.

Frontend tests (or lightweight integration checks):
1. `ApiClient`:
- `patch()` exists and behaves like `post`/`put`.
- Error parsing for JSON and non-JSON responses.
- Maintenance event dispatch for 503 remains intact.

2. App-level smoke:
- Admin loads and can patch model fields.
- Monitor loads and inspector fetches through shared client.

Acceptance criteria:
- New tests fail on current regressions and pass after fixes.

---

## Phase 7: Validation Runbook

1. Local dev validation:
- Start backend + one frontend app in Vite mode.
- Confirm no `/v1/v1` requests and successful API calls.

2. Docker validation:
- `docker-compose up --build` from `deploy/`.
- Validate all four app routes and core interactions.

3. Regression checklist:
- Workbench next/validate flow
- Explorer attributes/search/export
- Monitor velocity/irr/pipeline health/inspector
- Admin models patching, budget, kill switch, exports, uploads, VLM health list

4. Log verification:
- No recurring 401 for valid privileged sessions.
- No systemic 404 from malformed paths.

---

## Recommended Implementation Order

1. Phase 1 (proxy rewrite)
2. Phase 4 (`ApiClient.patch`)
3. Phase 2 (auth alignment)
4. Phase 3 (monitor inspector refactor)
5. Phase 5 (error UX hardening)
6. Phase 6 (tests)
7. Phase 7 (full validation)

Rationale:
- Fixes broadest breakage first, then restores missing client capability, then resolves privileged access and partial-panel failures, then hardens diagnostics and test guardrails.

---

## Risk Notes

1. Auth token propagation to static frontend must be handled carefully:
- Avoid embedding secrets directly in bundled JS.
- Prefer runtime injection or session-based server-issued tokens.

2. Prefix middleware behavior can mask path mistakes:
- Keep one canonical path strategy and test both dev and container routing.

3. Monitor/Admin rely heavily on privileged calls:
- Any auth mismatch appears as multi-page failure; prioritize observability.

---

## Done Definition

This issue is considered resolved when:
1. All four apps load without `"API Request Failed"` in normal startup flow.
2. No malformed `/v1/v1/...` requests are emitted in dev tools.
3. Privileged pages work with valid auth and fail clearly with invalid auth.
4. Admin PATCH workflows function end-to-end.
5. Monitor inspector works consistently via shared API client path.
6. Added tests protect against these regressions.
